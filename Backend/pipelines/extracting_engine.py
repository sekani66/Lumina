import fitz 
import re
import asyncio

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from pipelines import llm_gateway as gateway
from prompts.extracting_engine_prompts import ExtractingPrompt

MAX_PDF_BYTES = 30 * 1024 * 1024    # 30 MB hard cap

# Data models 
@dataclass
class RawSpan:
    """A single text span extracted from a PDF page.

    One span corresponds to a contiguous run of text sharing the same font
    size and weight, as reported by PyMuPDF's ``page.get_text("dict")``.
    Spans are the raw unit that later stages group into sections.

    Attributes:
        page: 1-indexed page number the span was found on.
        text: The stripped text content of the span.
        font_size: Font size in points, rounded to 1 decimal place.
        is_bold: Whether the span's font flags indicate bold weight.
    """
    page:      int
    text:      str
    font_size: float
    is_bold:   bool

@dataclass
class Section:
    """A structured content block — maps to a chapter or lesson cluster.

    Produced by ``_segment_into_sections`` and enriched afterwards with
    per-section key terms.

    Attributes:
        title: The heading text that introduces this section.
        level: Heading depth — 1 = chapter, 2 = section, 3 = sub-section.
        page_start: 1-indexed page number where the heading appears.
        body_text: Concatenated body text belonging to this section,
            i.e. all span text encountered before the next heading.
        key_terms: Heuristically extracted key terms local to this
            section's body text (populated after segmentation).
    """
    title:      str
    level:      int        # 1 = chapter, 2 = section, 3 = sub-section
    page_start: int
    body_text:  str = ""
    key_terms:  List[str] = field(default_factory=list)

@dataclass
class ExtractionResult:
    """Output of Stages 1+2: raw structural data, no LLM involved.

    This is the fully-parsed, structured representation of a source PDF,
    ready to be summarized (``build_source_summary``) or handed to the
    Stage 3 LLM lesson generator.

    Attributes:
        inferred_title: Best-guess document title (from metadata or
            first-page heuristics).
        inferred_subject: Best-guess subject, matched against a fixed
            keyword list, or "General" if nothing matched.
        inferred_grade: Best-guess grade/level string (e.g. "Grade 10"),
            or "Not specified" if no pattern matched.
        total_pages: Total number of pages in the source PDF.
        sections: Ordered list of detected sections (or a single
            fallback section if no headings were detected).
        key_concepts: Document-wide heuristic key terms/acronyms.
        full_text: All extracted span text concatenated with spaces.
    """
    inferred_title:   str
    inferred_subject: str
    inferred_grade:   str
    total_pages:      int
    sections:         List[Section]
    key_concepts:     List[str]
    full_text:        str


# Stage 1: PyMuPDF parse 
def _extract_spans(file_bytes: bytes) -> Tuple[fitz.Document, List[RawSpan]]:
    """Open a PDF from raw bytes and extract all text spans with font metadata.

    Walks every page's ``get_text("dict")`` block/line/span tree, keeping
    only text blocks (type 0) and skipping spans whose stripped text is
    shorter than 2 characters.

    Args:
        file_bytes: Raw bytes of the source PDF file.

    Returns:
        A tuple of:
            - The open ``fitz.Document`` (caller is responsible for
              closing it, e.g. via ``extract_from_pdf``'s try/finally).
            - A flat list of ``RawSpan`` objects in document order.
    """
    doc: fitz.Document = fitz.open(stream=file_bytes, filetype="pdf")
    spans: List[RawSpan] = []
    print("now extrating text")
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        for blk in page.get_text("dict")["blocks"]:
            if blk.get("type") != 0:   # 0 = text block, 1 = image block
                continue
            for line in blk.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if len(text) < 2:
                        continue
                    spans.append(RawSpan(
                        page=page_idx + 1,
                        text=text,
                        font_size=round(span.get("size", 12.0), 1),
                        is_bold=bool(span.get("flags", 0) & 16),
                    ))
    return doc, spans

def _infer_metadata( doc: fitz.Document, first_page_text: str, ) -> Tuple[str, str, str]:
    """Infer course title, subject, and grade/level.

    Uses, in order:
        1. PDF XMP/info metadata (for title).
        2. First-page text heuristics (for title fallback, subject, and
           grade/level, via regex and keyword matching).

    Args:
        doc: The open ``fitz.Document``, used to read ``doc.metadata``.
        first_page_text: All span text from page 1, space-joined.

    Returns:
        A ``(title, subject, grade)`` tuple:
            - title: from PDF metadata, or the first sufficiently long
              line of first-page text, or "Untitled Document".
            - subject: matched against a fixed keyword list against the
              combined title + first-page text (case-insensitive), or
              "General" if nothing matched.
            - grade: parsed from patterns like "Grade 10", "Gr. 10", or
              "Year 10" in the first-page text, or "Not specified".
    """
    meta  = doc.metadata or {}
    title = meta.get("title", "").strip() 
    
    print("Trying to detect grade")
    
    # Grade or level detection
    gm = re.search(
        r"[Gg]rade\s+(\d{1,2})|[Gg]r\.?\s*(\d{1,2})|[Yy]ear\s+(\d{1,2})",
        first_page_text,
    )
    if gm:
        num   = gm.group(1) or gm.group(2) or gm.group(3)
        grade = f"Grade {num}"
    else:
        grade = "Not specified"

    # Subject detection
    subject_keywords = [
        "Mathematics", "Physics", "Chemistry", "Biology",
        "Computer Science", "Economics", "History", "Geography",
        "English", "Accounting", "Engineering", "Statistics",
        "Life Sciences", "Business Studies",
    ]
    combined = (title + " " + first_page_text).lower()
    subject  = next((s for s in subject_keywords if s.lower() in combined), "General")

    # Title fallback
    if not title:
        lines = [ln.strip() for ln in first_page_text.split("\n") if len(ln.strip()) > 6]
        title = lines[0] if lines else "Untitled Document"

    return title, subject, grade

# Stage 2: Structural chunker
def _build_heading_map(spans: List[RawSpan]) -> Dict[float, int]:
    """Detect heading font sizes statistically.

    Treats the most common font size (among spans with text longer than
    3 characters) as "body text", then treats any font size at least
    1pt larger as a candidate heading size. The 3 largest such sizes are
    ranked and assigned heading levels 1 (largest) through 3.

    Args:
        spans: All extracted spans for the document.

    Returns:
        A mapping of font size -> heading level (1-3). Empty if there
        are no spans with text longer than 3 characters.
    """
    sizes = [s.font_size for s in spans if len(s.text) > 3]
    if not sizes:
        return {}
    body_sz = max(set(sizes), key=sizes.count)
    # Require a gap of at least 1 pt to qualify as a heading
    bigger  = sorted({sz for sz in sizes if sz > body_sz + 0.9}, reverse=True)
    return {sz: (i + 1) for i, sz in enumerate(bigger[:3])}

def _segment_into_sections( spans: List[RawSpan], heading_map: Dict[float, int], ) -> List[Section]:
    """Group spans into sections by walking them sequentially.

    A new ``Section`` is started whenever a heading span is encountered —
    either because its font size is present in ``heading_map``, or because
    it looks like a bold structural heading (bold, >= 14pt, <= 15 words)
    even if its size wasn't statistically flagged. All non-heading spans
    accumulate as body text for the current section.

    A section (including the final one) is only kept if its accumulated
    body text has at least 15 words, to filter out spurious/empty
    headings-only fragments.

    Args:
        spans: All extracted spans for the document, in document order.
        heading_map: Font size -> heading level mapping from
            ``_build_heading_map``.

    Returns:
        Ordered list of detected ``Section`` objects. If no sections
        survive the 15-word filter, falls back to a single
        "Document Content" section containing all span text.
    """
    sections:   List[Section]    = []
    current:    Optional[Section] = None
    body_parts: List[str]         = []
    
    print("Segmenting sections")
    for sp in spans:
        level = heading_map.get(sp.font_size, 0)
        # Catch bold structural headings
        if not level and sp.is_bold and sp.font_size >= 14 and len(sp.text.split()) <= 15:
            level = 2
        if level and len(sp.text) > 2:
            # Flush the previous section (same 15 word guard as mid-stream)
            if current is not None:
                current.body_text = " ".join(body_parts).strip()
                if len(current.body_text.split()) >= 15:
                    sections.append(current)
            current    = Section(title=sp.text, level=level, page_start=sp.page)
            body_parts = []
        else:
            body_parts.append(sp.text)

    # Flush final section
    if current is not None:
        current.body_text = " ".join(body_parts).strip()
        if len(current.body_text.split()) >= 15:
            sections.append(current)
    
    # Fallback: no structural headings detected treat whole doc as one block
    if not sections:
        full = " ".join(sp.text for sp in spans)
        sections = [Section(
            title="Document Content",
            level=1,
            page_start=1,
            body_text=full,
        )]
    return sections


def _extract_key_terms(text: str, n: int = 15) -> List[str]:
    """Heuristically extract likely key terms from a block of text.

    Matches two patterns and unions the results into a set (so duplicates
    collapse and order is not preserved from the source text):
        * Title-Case multi-word phrases (e.g. "Kinetic Energy").
        * Acronyms of 2-6 uppercase letters (e.g. "DNA", "HTTP").

    A small fixed list of single-token noise words (e.g. "The", "Figure",
    "Table") is filtered out; multi-word phrases that happen to start
    with one of these are kept.

    Args:
        text: The text to scan for key terms.
        n: Maximum number of terms to return.

    Returns:
        Up to ``n`` matched terms, sorted alphabetically.
    """
    print("Extracting key terms")
    found: set = set()
    # Title-Case multi-word phrase pattern
    for m in re.finditer(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", text):
        found.add(m.group())
    # Acronym pattern
    for m in re.finditer(r"\b([A-Z]{2,6})\b", text):
        found.add(m.group())

    # Only remove single-token noise, not phrases that happen to start with one
    noise_tokens = {
        "The", "This", "That", "With", "From", "Page",
        "Figure", "Table", "Example",
    }
    cleaned = sorted(t for t in found if t not in noise_tokens)
    return cleaned[:n]


# Stages 1 and 2 entry point 
def extract_from_pdf(file_bytes: bytes) -> ExtractionResult:
    """Run Stages 1+2: parse a PDF into structured, LLM-free data.

    Opens the PDF with PyMuPDF, extracts all text spans with font
    metadata, infers title/subject/grade, detects heading structure,
    segments the document into named sections, and extracts both
    document-wide and per-section key terms. Always closes the opened
    PyMuPDF document, even on error.

    Args:
        file_bytes: Raw bytes of the source PDF file.

    Returns:
        A populated ``ExtractionResult``.

    Raises:
        ValueError: If no extractable text spans were found (e.g. the
            PDF is an image-only scan with no OCR support yet).
    """
    doc: Optional[fitz.Document] = None
    
    print("Extracting from pdf")
    try:
        doc, spans = _extract_spans(file_bytes)
        pages      = len(doc)

        if not spans:
            raise ValueError(
                "No extractable text found in this PDF. "
                "It may be an image-only scan. "
                "OCR support (PaddleOCR / AMD ROCm) is on the roadmap."
            )

        full_text        = " ".join(sp.text for sp in spans)
        first_page_text  = " ".join(sp.text for sp in spans if sp.page == 1)

        title, subject, grade = _infer_metadata(doc, first_page_text)
        heading_map            = _build_heading_map(spans)
        sections               = _segment_into_sections(spans, heading_map)
        key_concepts           = _extract_key_terms(full_text)

        # Per-section key terms (used in source_summary and prerequisite prompt)
        for sec in sections:
            sec.key_terms = _extract_key_terms(sec.body_text, n=6)

        return ExtractionResult(
            inferred_title=title,
            inferred_subject=subject,
            inferred_grade=grade,
            total_pages=pages,
            sections=sections,
            key_concepts=key_concepts,
            full_text=full_text,
        )
    finally:
        if doc is not None:
            doc.close()

# Source summary builder 
def build_source_summary(result: ExtractionResult, max_sections: int = 16) -> str:
    """Produce a compact plain-text digest of the extracted PDF structure.

    Passed to ``/create/course/prerequisites`` and ``/create/course`` so
    both LLM calls are grounded in the real source content rather than
    invented topics. Unlike ``_build_section_digest``, this includes a
    header block plus per-section key terms and truncates each section's
    body to 250 words.

    Args:
        result: The ``ExtractionResult`` to summarize.
        max_sections: Maximum number of sections to include in full;
            any remaining sections are noted with a count only.

    Returns:
        A newline-joined plain-text summary string.
    """
    
    print("Building source summary")
    lines = [
        f"COURSE RESOURCE: {result.inferred_title}",
        f"Subject : {result.inferred_subject}",
        f"Level   : {result.inferred_grade}",
        f"Pages   : {result.total_pages}  |  Sections detected: {len(result.sections)}",
        f"Global key concepts: {', '.join(result.key_concepts[:12])}",
        "",
        "=== CONTENT STRUCTURE ===",
    ]
    for i, sec in enumerate(result.sections[:max_sections]):
        words    = sec.body_text.split()
        snippet  = " ".join(words[:250])
        ellipsis = "…" if len(words) > 250 else ""
        lines += [
            f"\n[{i + 1}. Level-{sec.level} | p.{sec.page_start}] {sec.title}",
            f"  Key terms : {', '.join(sec.key_terms) or '—'}",
            f"  Content   : {snippet}{ellipsis}",
        ]
    if len(result.sections) > max_sections:
        lines.append(
            f"\n… {len(result.sections) - max_sections} additional sections not shown."
        )
    return "\n".join(lines)


# Stage 3: LLM Lesson Generator 
def _build_section_digest(result: ExtractionResult, max_sections: int = 16) -> str:
    """Build the section digest passed to the Stage 3 LLM lesson generator.

    Similar in spirit to ``build_source_summary`` but formatted for LLM
    consumption rather than human display: sections are labeled
    positionally ("Section N") and each section's body is truncated to
    300 words (vs. 250 in the human-facing summary). Per-section key
    terms are included but no global-summary-only fields are added.

    Args:
        result: The ``ExtractionResult`` to digest.
        max_sections: Maximum number of sections to include; sections
            beyond this are silently omitted (no "N more" note).

    Returns:
        A newline-joined plain-text digest string.
    """
    print("Now on build section digest")
    lines = [
        f"Course resource : {result.inferred_title}",
        f"Subject         : {result.inferred_subject}",
        f"Level           : {result.inferred_grade}",
        f"Total pages     : {result.total_pages}",
        f"Global concepts : {', '.join(result.key_concepts[:12])}",
        "",
        "=== SECTION DIGEST ===",
    ]
    for i, sec in enumerate(result.sections[:max_sections]):
        words   = sec.body_text.split()
        snippet = " ".join(words[:300])
        cont    = "…" if len(words) > 300 else ""
        lines += [
            f"\n[Section {i + 1} | L{sec.level} | p.{sec.page_start}]",
            f"Title : {sec.title}",
            f"Terms : {', '.join(sec.key_terms) or '—'}",
            f"Text  : {snippet}{cont}",
        ]
    return "\n".join(lines)


async def generate_course_from_extraction(
        result: ExtractionResult,
        model: Optional[str] = None,
    ) -> Dict:
    """Generate a preliminary course plan from the extracted PDF digest.

    Builds the section digest via ``_build_section_digest`` and sends it
    to the LLM gateway as a JSON-mode completion, using the course-plan
    system prompt.

    No longer takes an ``openai_client`` param or wraps a sync call in
    ``asyncio.to_thread`` — the gateway's providers are natively async,
    so this just awaits ``gateway.complete_json()`` directly.

    Args:
        result: The ``ExtractionResult`` to build a course plan from.
        model: A logical alias ("fast"/"default"/"reasoning") or a
            literal vendor model id; omit to use the gateway's
            configured default.

    Returns:
        The parsed JSON course plan as a dict.

    Raises:
        RuntimeError: If the gateway call fails. If the failure was due
            to truncation (response exceeded ``max_tokens``), the error
            message specifically advises reducing source material scope
            and retrying; otherwise the original gateway error message
            is preserved.
    """
    digest = _build_section_digest(result)

    try:
        return await gateway.complete_json(
            digest,
            model=model,
            system=ExtractingPrompt.PDF_COURSE_SYSTEM_PROMPT,
            max_tokens=3000,
            temperature=0.35,
        )
    except gateway.LLMGatewayError as exc:
        if "truncated" in str(exc).lower():
            raise RuntimeError(
                "Course plan generation was truncated (response exceeded "
                "max_tokens). Reduce source material scope and retry."
            ) from exc
        raise RuntimeError(str(exc)) from exc


# Stage 4: Full pipeline entry point 
async def run_extraction_pipeline( file_bytes: bytes,
        model: Optional[str] = None,
    ) -> Dict:
    """Run the full pipeline: raw PDF bytes to structured output dict.

    Stages:
        1-2. Parse and segment the PDF (``extract_from_pdf``) — CPU-bound,
             so it's offloaded to a thread to keep the event loop free.
        Digest. Build the human-readable source summary
             (``build_source_summary``) — also offloaded to a thread.
        3. Generate a preliminary course plan via the LLM gateway
             (``generate_course_from_extraction``) — natively async.

    Args:
        file_bytes: Raw bytes of the source PDF file.
        model: Optional logical alias or literal vendor model id,
            forwarded to ``generate_course_from_extraction``.

    Returns:
        A dict with keys:
            - "extraction_meta": summary metadata (title, subject,
              grade, page count, section count).
            - "source_summary": the human-readable digest string.
            - "preliminary_plan": the LLM-generated course plan dict.
            - "key_concepts": document-wide heuristic key terms.
    """
    print("Now on full pipeline entry point")
    # Stages 1 and 2: CPU-bound; offload so the event loop stays free
    extraction: ExtractionResult = await asyncio.to_thread(
        extract_from_pdf, file_bytes
    )

    # Build the compact digest string reused by all downstream LLM calls
    source_summary: str = await asyncio.to_thread(
        build_source_summary, extraction
    )

    # Stage 3 — async LLM lesson generation via the gateway
    preliminary_plan: Dict = await generate_course_from_extraction(
        extraction, model
    )

    return {
        "extraction_meta": {
            "inferred_title":   extraction.inferred_title,
            "inferred_subject": extraction.inferred_subject,
            "inferred_grade":   extraction.inferred_grade,
            "total_pages":      extraction.total_pages,
            "sections_count":   len(extraction.sections),
        },
        "source_summary":  source_summary,
        "preliminary_plan": preliminary_plan,
        "key_concepts":    extraction.key_concepts,
    }