"""
Lumina Answer Engine  (aligned with lesson_engine shape)
═══════════════════════════════════════════════════════════════════════════════
PURPOSE
  The real-time teaching layer that turns learner interruptions into genuine
  instructional moments. When a learner asks a question mid-lesson, this engine:

    1.  Reads the question within the full context of the active lesson section
    2.  Detects misconceptions hiding inside the question (the question behind
        the question) before answering the surface request
    3.  Answers in the natural voice of a real teacher — warm, patient, present
    4.  Emits the answer as SPEAK / WRITE / PAUSE / AWAIT_RESPONSE events —
        the SAME event vocabulary lesson_engine.py uses — so streaming_engine
        plays an answer exactly like it plays lesson content. No special-cased
        rendering path on the frontend.
    5.  Illustrates every explanation with at least one concrete example
    6.  Sends learner replies to the understanding-classifier AGENT — never a
        static phrase list — because confirmations show up in too many shapes
        for keyword matching to ever be reliable
    7.  Grades direct answers to its own AWAIT_RESPONSE probes as
        CORRECT / PARTIAL / INCORRECT, acknowledges the result out loud, and
        keeps teaching if the learner got it wrong
    8.  Escalates with a completely different teaching approach if not confirmed
    9.  After MAX_EXAMPLES_BEFORE_PROBE attempts, probes to locate the exact
        confusion point rather than blindly repeating another version
   10.  Times out gracefully — a learner who never replies is not held hostage
        forever; see TIMEOUT POLICY below

  This engine is NOT a Q&A chatbot. It is a teaching presence that holds the
  learner in the concept until it actually lands — exactly as a great human
  teacher would it a real time classroom.

═══════════════════════════════════════════════════════════════════════════════
TIMEOUT POLICY  (new)
  A learner who has gone quiet should never freeze the lesson forever.
  The caller (routes.py / the session/frontend layer) tracks wall-clock time
  and passes `seconds_since_prompt` — how long it has been since the last
  AWAIT_RESPONSE / understanding probe was issued — into handle_answer_session.

    seconds_since_prompt >= CONFIRMATION_TIMEOUT_SECONDS  (default 1min)
    and learner_response is blank
        │
        ├─ examples_given >= MAX_EXAMPLES_BEFORE_PROBE
        │       → RESUME the lesson. We've already tried enough angles;
        │         silence here is treated as "good enough, move on".
        │
        ├─ examples_given <  MAX_EXAMPLES_BEFORE_PROBE
        │  and a timeout grace example hasn't been used yet
        │       → give exactly ONE more example (the "grace" example),
        │         re-ask the understanding probe, re-arm the clock
        │         (`timeout_grace_used: true` comes back in the envelope —
        │         the caller passes it straight back on the next call)
        │
        └─ timeout_grace_used is already true and the learner is STILL
           silent on the second timeout
                → RESUME the lesson unconditionally. One grace attempt is
                  the limit — we do not wait twice on a silent learner.

  A non-blank learner_response always wins over the timer — a real reply,
  however late, is read normally by classify_understanding().

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE

  ┌──────────────────────────────────────────────────────────────────────┐
  │           LESSON PLAN  (from lesson_engine.py)                       │
  └──────────────────────────┬───────────────────────────────────────────┘
                             │
              generate_lesson()  returns  →  lesson starts streaming NOW
                             │
                             ├────────────────────────────────────────────┐
                             │                                            │
                             ▼                                            ▼
              launch_background_anticipation(lesson)        STREAMING STARTS IMMEDIATELY
                 (asyncio.create_task — fire and forget,        (no waiting on the bank)
                  never awaited before the lesson starts)
                             │
                             ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │   QUESTION BANK TASK  — builds in the background while the lesson   │
  │   is already on screen. handle_answer_session() checks task.done()  │
  │   and uses it opportunistically — it NEVER awaits/blocks on it.     │
  └──────────────────────────┬───────────────────────────────────────────┘
                             │
  ── LIVE LESSON ─────────── │ ────────────────────────────────────────
                             │
             Learner asks question mid-lesson
                             │
             classify_question()  ← detect type + hidden misconception
                             │
             search_question_bank()  ← bank task done? fast cache hit?
                    ├─ HIT  →  serve pre-warmed answer instantly
                    └─ MISS →  answer_learner_question()
                             │
              Answer returned as SPEAK/WRITE/PAUSE/AWAIT_RESPONSE steps
              (identical shape to lesson_engine sections) + resume pointer
                             │
             Learner replies, answers the probe, or stays silent
                             │
        ┌────────────────────┼────────────────────────┬─────────────────┐
        │                    │                        │                 │
   TIMEOUT (silent)    classify_understanding()   probe answered      probe answered
   → grace example      (LLM agent — no             CORRECTLY          INCORRECTLY
     or RESUME           keyword list)                  │                  │
                              │                    acknowledge +      acknowledge +
                              │                    RESUME LESSON      escalate_with_example()
        ┌─────────────────────┼─────────────────────────┐         (new approach, references
        │                     │                          │          the specific wrong answer)
     CONFIRMED            UNCERTAIN              NOT_CONFIRMED
        │                     │                          │
  RESUME LESSON        probe_specific()        escalate_with_example()
                                                          │
                                             (repeat understanding check)
                                                          │
                                      (after MAX_EXAMPLES_BEFORE_PROBE)
                                                          │
                                              probe_confusion_point()
                                                          │
                                          generate_micro_explanation()

═══════════════════════════════════════════════════════════════════════════════
EVENT SCHEMA  (identical vocabulary to lesson_engine.py — see that module's
docstring for the full event-type reference)

  Every explanation this engine produces is shaped as:
    steps: [ { id, objective, events: [ {type, content, sync_with_previous} ] } ]

  using the SAME event types as a lesson section: SPEAK, WRITE, HIGHLIGHT,
  UNDERLINE, CIRCLE, ANNOTATE, ERASE, REVEAL, PAUSE, AWAIT_RESPONSE.
  The final step of any explanation always ends in exactly one
  AWAIT_RESPONSE event — that IS the understanding probe. 

  Top-level envelope sent to the frontend for an in-progress explanation:
  {
    "type":     "answer",
    "question": "<the learner's original question>",
    "resume":   { "lesson_id": "...", "section_id": "...", "step_id": "..." },
    "sections": [ { "id", "type", "title", "purpose", "steps": [...] } ]
  }

  `resume` tells the frontend exactly where to drop the learner back into the
  main lesson once this explanation thread finishes — it travels alongside
  the explanation on every turn, not just on the final RESUME action, so the
  frontend never loses track of the return point mid-conversation.

═══════════════════════════════════════════════════════════════════════════════
QUESTION TYPES
  WHY       — "Why did we divide by 3?" — causal/conceptual reasoning
  HOW       — "How does this formula work?" — procedural understanding
  WHAT_IS   — "What is a discriminant?" — definition seeking
  WHAT_IF   — "What if x were negative?" — hypothetical probing
  CLARIFY   — "I got lost there" — re-explanation needed
  ERROR     — "Isn't that +2, not −2?" — misconception / error challenge
  STEP      — "What happened between step 2 and 3?" — gap in follow-through
  GENERAL   — Catch-all

TEACHING APPROACHES  (rotated on each escalation — never repeats)
  ALGEBRAIC  — Direct manipulation using notation from the board
  ANALOGY    — Everyday real-world parallel, then bridge back to the math
  NUMERICAL  — Plug in the simplest concrete numbers and trace every step
  CONTRAST   — Show what goes wrong if this step is skipped or changed
  BACKWARDS  — Start from the answer, reverse-engineer the reason
  STORY      — Embed the concept inside a real-world word problem narrative
  VISUAL     — Describe geometry, shape, direction, or spatial intuition

UNDERSTANDING STATES
  CONFIRMED     — Learner explicitly or implicitly shows comprehension, OR
                  correctly answered the AWAIT_RESPONSE probe
  PENDING       — Learner hasn't responded yet (answer just given)
  UNCERTAIN     — Ambiguous reply; needs a probe
  NOT_CONFIRMED — Learner signals confusion, OR answered the probe incorrectly
  ESCALATED     — Multiple examples given; locate specific confusion point

PROBE OUTCOMES  (new — grading a direct answer to our own probe question)
  CORRECT        — Learner's answer to the posed question is right
  PARTIAL        — On the right track but incomplete / minor slip
  INCORRECT      — Wrong — keep teaching, do not resume
  NOT_APPLICABLE — The reply wasn't an attempt at the probe at all
                   (e.g. a generic "okay" or a brand-new question)

═══════════════════════════════════════════════════════════════════════════════
DOWNSTREAM WIRING  (routes.py)
  POST /lesson/generate         → lesson_engine.generate_lesson()
  POST /lesson/start            → begin streaming the lesson AND, in the same
                                   request handler, call
                                   launch_background_anticipation(lesson)
                                   WITHOUT awaiting it. Old flow was
                                       generate → anticipate → start
                                   New flow is
                                       generate → start  ‖  anticipate (bg)
  POST /answer/ask              → handle_answer_session()   ← primary endpoint
  POST /answer/understand       → classify_understanding()
  POST /answer/escalate         → escalate_with_example()
  POST /answer/probe            → probe_confusion_point()
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pipelines import llm_gateway as gateway

from utils.answer_engine_helpers import  _strip_fences, _is_blank
from prompts.answer_engine_prompts import (
    _CLASSIFY_SYSTEM,
    _CONFIRM_CHECK_SYSTEM,
    _ANSWER_SYSTEM,
    _ANTICIPATE_SYSTEM,
    _ESCALATE_SYSTEM,
    _UNDERSTAND_SYSTEM,
    _PROBE_SYSTEM,
    _MICRO_SYSTEM
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────────────────────────────────────

class QuestionType(str, Enum):
    WHY      = "WHY"
    HOW      = "HOW"
    WHAT_IS  = "WHAT_IS"
    WHAT_IF  = "WHAT_IF"
    CLARIFY  = "CLARIFY"
    ERROR    = "ERROR"
    STEP     = "STEP"
    GENERAL  = "GENERAL"


class UnderstandingStatus(str, Enum):
    CONFIRMED     = "CONFIRMED"
    PENDING       = "PENDING"
    UNCERTAIN     = "UNCERTAIN"
    NOT_CONFIRMED = "NOT_CONFIRMED"
    ESCALATED     = "ESCALATED"


class TeachingApproach(str, Enum):
    ALGEBRAIC = "ALGEBRAIC"
    ANALOGY   = "ANALOGY"
    NUMERICAL = "NUMERICAL"
    CONTRAST  = "CONTRAST"
    BACKWARDS = "BACKWARDS"
    STORY     = "STORY"
    VISUAL    = "VISUAL"


class ProbeOutcome(str, Enum):
    CORRECT        = "CORRECT"
    PARTIAL        = "PARTIAL"
    INCORRECT      = "INCORRECT"
    NOT_APPLICABLE = "NOT_APPLICABLE"


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# After this many escalation examples, stop adding more and probe instead
MAX_EXAMPLES_BEFORE_PROBE: int = 3

# How long we wait, minutes, for a learner to respond to an understanding
# probe before the timeout policy kicks in (see module docstring). 
CONFIRMATION_TIMEOUT_SECONDS: float = 2

# Rotation order — first used on the initial answer, then cycled on escalation
APPROACH_PROGRESSION: List[str] = [
    TeachingApproach.ALGEBRAIC,
    TeachingApproach.ANALOGY,
    TeachingApproach.NUMERICAL,
    TeachingApproach.CONTRAST,
    TeachingApproach.BACKWARDS,
    TeachingApproach.STORY,
    TeachingApproach.VISUAL,
]

# Event types this engine is allowed to emit — identical vocabulary to
# lesson_engine.EVENT_TYPES, repeated here so this module has no hard import
# dependency on lesson_engine.py.
EVENT_TYPES: frozenset[str] = frozenset({
    "SPEAK", "WRITE", "HIGHLIGHT", "UNDERLINE", "CIRCLE",
    "ANNOTATE", "ERASE", "REVEAL", "PAUSE", "AWAIT_RESPONSE",
})

# ─────────────────────────────────────────────────────────────────────────────
# PRIVATE HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _select_next_approach(examples_given: int, previous_approach: Optional[str] = None) -> str:
    """
    Pick the next teaching approach. Rotates through APPROACH_PROGRESSION,
    skipping the previous one to guarantee a fresh angle every time.
    """
    idx = examples_given % len(APPROACH_PROGRESSION)
    approach = APPROACH_PROGRESSION[idx]
    if approach == previous_approach:
        approach = APPROACH_PROGRESSION[(idx + 1) % len(APPROACH_PROGRESSION)]
    return approach


def _format_section_context(section: Dict) -> str:
    """
    Render a lesson section as readable text for LLM context.
    Extracts relevant fields from the four-level lesson schema
    (section → steps → events) produced by lesson_engine.py.
    """
    parts: List[str] = [
        f"Section type  : {section.get('type', 'UNKNOWN')}",
        f"Title         : {section.get('title', '(none)')}",
        f"Purpose       : {section.get('purpose', '(none)')}",
    ]

    speaks: List[str] = []
    writes: List[str] = []
    objectives: List[str] = []
    annotations: List[str] = []

    for step in section.get("steps", []):
        if step.get("objective"):
            objectives.append(step["objective"])
        for event in step.get("events", []):
            etype = event.get("type", "")
            content = event.get("content")
            if not content:
                continue
            if etype == "SPEAK":
                speaks.append(content)
            elif etype == "WRITE":
                writes.append(content)
            elif etype == "ANNOTATE":
                annotations.append(content)

    if speaks:
        parts.append(f"Teacher said  : {speaks[0]}")
        if len(speaks) > 1:
            parts.append(f"              : {speaks[1]}")

    if writes:
        parts.append(f"Board math    : {'  ·  '.join(writes[:5])}")

    if objectives:
        parts.append(f"Step goals    : {' | '.join(objectives[:3])}")

    error_notes = [
        a for a in annotations
        if any(w in a.lower() for w in ("mistake", "error", "wrong", "common", "don't", "✗"))
    ]
    if error_notes:
        parts.append(f"Common error  : {error_notes[0]}")

    return "\n".join(parts)


def _build_lesson_summary(lesson: Dict) -> str:
    """One-paragraph summary of the lesson for context injection."""
    return (
        f"Lesson: {lesson.get('lesson_title', 'Unknown')} | "
        f"Subject: {lesson.get('subject', 'General')} | "
        f"Grade: {lesson.get('grade_level', '')} | "
        f"Goal: {lesson.get('goal', 'Deep Mastery')} | "
        f"Key concepts: {', '.join(lesson.get('key_concepts', []))}"
    )


def _make_speak_event(text: str) -> Dict:
    return {"type": "SPEAK", "content": text, "sync_with_previous": False}


def _wrap_answer_envelope(
    question: str,
    resume_pointer: Optional[Dict],
    steps: List[Dict],
    section_type: str,
    title: str,
    purpose: str,
    leading_speak: Optional[str] = None,
) -> Dict:
    """
    Build the top-level envelope handed to the frontend / streaming_engine.
    Shape matches lesson_engine sections exactly, plus the `resume` pointer
    that tells the frontend where to drop the learner back into the main
    lesson once this explanation thread is done.

    If `leading_speak` is given (e.g. an acknowledgment of a probe answer),
    it is injected as the very first event of the very first step.
    """
    steps = [dict(s) for s in steps]  # shallow copy, avoid mutating caller data
    if leading_speak:
        if steps:
            first_step = dict(steps[0])
            first_step["events"] = [_make_speak_event(leading_speak)] + list(first_step.get("events", []))
            steps[0] = first_step
        else:
            steps = [{
                "id": "ack_step",
                "objective": "Acknowledge the learner's response",
                "events": [_make_speak_event(leading_speak)],
            }]

    return {
        "type":     "answer",
        "question": question,
        "resume":   resume_pointer,
        "sections": [{
            "id":      f"answer_{uuid.uuid4().hex[:8]}",
            "type":    section_type,
            "title":   title,
            "purpose": purpose,
            "steps":   steps,
        }],
    }


def _extract_probe_question(steps: List[Dict]) -> Optional[str]:
    """
    Pull the literal text of the AWAIT_RESPONSE event out of a generated
    steps list — this is what gets passed into classify_understanding() on
    the learner's NEXT turn so it can grade a direct-answer attempt.
    """
    for step in reversed(steps):
        for event in reversed(step.get("events", [])):
            if event.get("type") == "AWAIT_RESPONSE":
                return event.get("content")
    return None

async def _llm_json(
    system: str,
    user: str,
    model: Optional[str] = None,
    temperature: float = 0.5,
    max_tokens: int = 2000,
) -> Dict:
    """
    LLM call that always returns a parsed dict, never raises on bad JSON.

    Deliberately calls gateway.complete() rather than gateway.complete_json():
    the gateway's JSON helper raises json.JSONDecodeError on malformed output,
    but every caller in this file expects a soft {"raw_text", "_parse_error"}
    fallback instead — answer_engine treats a parse failure as recoverable
    (e.g. classify_understanding() still has sensible defaults to fall back
    on), not as a hard error worth a 500.
    """
    try:
        raw = await gateway.complete(
            user,
            model=model,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format="json",
        )
    except gateway.LLMGatewayError as exc:
        if "truncated" in str(exc).lower():
            raise RuntimeError(
                "Answer engine response was truncated (response exceeded "
                "max_tokens). Reduce max_tokens or simplify the prompt and retry."
            ) from exc
        raise RuntimeError(str(exc)) from exc

    try:
        parsed = json.loads(_strip_fences(raw))
    except json.JSONDecodeError:
        return {"raw_text": raw, "_parse_error": True}

    if not isinstance(parsed, dict):
        # Valid JSON, but not an object — e.g. the model wrapped its answer
        # in a bare string or emitted a list. json.loads() happily returns
        # that str/list/int as-is, which silently breaks every caller in
        # this file (they all do result.get(...) assuming a dict). Treat
        # this the same as a parse failure rather than let a `'str' object
        # has no attribute 'get'` crash surface three call-frames away.
        logger.warning(
            "_llm_json: model returned valid JSON that wasn't an object "
            "(type=%s) — treating as a parse failure. raw=%r",
            type(parsed).__name__, raw[:500],
        )
        return {"raw_text": raw, "_parse_error": True}

    return parsed

_INLINE_MATH_RE = re.compile(
    r'(?:'
    r'\d+\s*x\s*\^?\s*\d+'   # 4x^2, 3x2
    r'|x\s*\^+\s*\d+'         # x^3
    r'|\\frac\{'               # LaTeX fraction
    r'|P\s*\(x\)\s*='         # P(x) = ...
    r'|\d+\s*x\b'             # 5x (lone term)
    r')',
    re.IGNORECASE,
)

# Leading filler words that often precede an equation in natural speech
# ("say y = ...", "consider x^2 - 4x + 4 = 0, ...") — stripped once a
# clause is confirmed to be an equation, so the WRITE event shows just
# the math, not the narration around it.
_EQUATION_FILLER_LEAD_RE = re.compile(
    r'^\s*(?:say|like|such as|for example|e\.g\.,?|consider|that\'?s|that is|'
    r'imagine|suppose)\s+',
    re.IGNORECASE,
)


def _extract_equation_clauses(text: str) -> List[str]:
    """
    Best-effort extraction of full equation-like clauses from natural
    SPEAK narration, e.g. "...say y = x² - 5x + 6, what do..." yields
    ["y = x² - 5x + 6"].

    Unlike _INLINE_MATH_RE (which looks for caret-style exponent patterns
    and grabs only short fragments — built for redacting AWAIT_RESPONSE
    text), this targets whole equations regardless of notation style
    (it doesn't care whether the model wrote x^2 or the unicode x²), since
    its job is to recover something WRITE-able, not to pattern-match a
    specific syntax.

    The "=" sign is the signal: real narration rarely contains one, while
    an equation reliably does. We split on sentence/comma boundaries (the
    natural place narration ends and an aside or question begins), keep
    only clauses containing "=" with real content on both sides, then
    strip the conversational lead-in words ("say", "consider", ...) that
    so often introduce a new example.
    """
    clauses = re.split(r'[,.;!?]', text)
    found: List[str] = []
    for clause in clauses:
        clause = clause.strip()
        if not clause or "=" not in clause:
            continue
        lhs, _, rhs = clause.partition("=")
        if not re.search(r"[A-Za-z0-9]", lhs) or not re.search(r"[A-Za-z0-9]", rhs):
            continue
        clause = _EQUATION_FILLER_LEAD_RE.sub("", clause).strip()
        if clause:
            found.append(clause)
    return found


def _strip_narrative_lead_tokens(clause: str) -> str:
    """
    Strip leading narration word-by-word from a clause already confirmed by
    _extract_equation_clauses to contain an equation, WITHOUT risking a cut
    into the equation itself.

    This exists because _split_narrative_prefix (used elsewhere for
    model-authored WRITE content) locates the expression start via
    _EXPR_START_RE, which only matches a single identifier immediately
    before "=" — correct for a single-term LHS like "f(x) = ...", but wrong
    for a multi-term LHS like "2x + 3y = 12": it finds "y =" instead of the
    true start, truncating "2x + 3" into the discarded "narrative" half and
    leaving a mangled "y = 12" on the board.

    This walks tokens from the front and drops one only while it is purely
    alphabetic AND present in _WRITE_NARRATIVE_WORDS. The moment a token
    fails that test — a number, a variable glued to a coefficient like
    "2x", an operator, or simply a word outside the narration vocabulary —
    the strip stops immediately, so the equation's own tokens are never
    consumed. Less exhaustive than _split_narrative_prefix on narration
    that isn't in the known word list, but it never mangles the math.
    """
    tokens = clause.split()
    idx = 0
    while idx < len(tokens):
        bare = tokens[idx].strip(",.;:!?").lower()
        if bare and bare.isalpha() and bare in _WRITE_NARRATIVE_WORDS:
            idx += 1
            continue
        break
    return " ".join(tokens[idx:]) if idx else clause


def _normalize_math(s: str) -> str:
    """Whitespace-insensitive comparison key for matching equation text
    against what's already been WRITten (e.g. "x^2 - 5x+6" == "x^2-5x + 6")."""
    return re.sub(r"\s+", "", s)


def _equation_already_on_board(key: str, written_keys: set) -> bool:
    """
    True if `key` (a normalized clause extracted from speech) refers to an
    equation already covered by something in `written_keys` (normalized
    WRITE contents). Uses substring containment rather than strict equality
    because clause extraction can't perfectly strip every narration prefix
    ("so we solve 0 = 2x² - 4x + 2" vs the WRITE event's bare
    "0 = 2x² - 4x + 2") — the equation's core text still appears verbatim
    as a substring either way, so containment in either direction is a
    reliable match without requiring exact-string equality.
    """
    return any(key == w or key in w or w in key for w in written_keys)

def _merge_board_state(board_state: Optional[List[str]], steps: List[Dict]) -> List[str]:
    """Accumulate this turn's WRITE contents into the persisted board_state,
    skipping anything that normalizes to something already present. Round-
    trips through the frontend like examples_given/approaches_used."""
    merged = list(board_state or [])
    seen = {_normalize_math(s) for s in merged}
    for step in steps:
        for event in step.get("events", []):
            if event.get("type") == "WRITE" and event.get("content"):
                key = _normalize_math(event["content"])
                if key not in seen:
                    seen.add(key)
                    merged.append(event["content"])
    return merged


_STANDALONE_NUMBER_RE = re.compile(r'(?<![\w.])\d+(?:\.\d+)?(?![\w])')


def _find_ungrounded_probe_numbers(steps: List[Dict], known_text: str) -> List[str]:
    """
    Best-effort detection of a hypothetical numeric value introduced only
    inside AWAIT_RESPONSE content and never written to the board — e.g.
    "...if the rise doubled to 16?" when "16" appears nowhere on the board.

    The schema rules already prohibit this (AWAIT_RESPONSE content must be a
    short verbal question only; any number/equation it refers to must already
    be WRITten first) but nothing enforced it in code, unlike the HIGHLIGHT
    grounding check. Unlike that check, this one can't safely auto-correct —
    we don't know what WRITE content the model intended (e.g. "Rise = 16" vs
    just "16" vs something else entirely), so fabricating one risks putting
    wrong content on the board. This only detects and logs loudly for
    monitoring/prompt-iteration; it does not trigger a retry, to avoid
    burning an extra LLM call on every benign number mention — plenty of
    numbers in a probe question are harmless (times, counts, step numbers)
    rather than an invented value change.

    known_text is the combined text of everything already on the board
    (prior board_state + every WRITE emitted across this turn's steps), so a
    match is only flagged if it doesn't appear anywhere in that text.
    """
    flagged: List[str] = []
    for step in steps:
        for event in step.get("events", []):
            if event.get("type") != "AWAIT_RESPONSE":
                continue
            content = event.get("content") or ""
            for m in _STANDALONE_NUMBER_RE.finditer(content):
                num = m.group(0)
                if len(num) < 2:
                    continue  # single digits are too noisy to flag reliably
                if num not in known_text:
                    flagged.append(num)
    return flagged


def _find_ungrounded_highlights(
    steps: List[Dict], known_keys: set
) -> List[str]:
    """
    Returns the content of any HIGHLIGHT (or CIRCLE/UNDERLINE/BOX-style
    reference) event whose target doesn't normalize-match anything the
    learner has actually already seen (known_keys = real section WRITEs +
    board_state, normalized via _normalize_math).

    HIGHLIGHT is a claim that "this is already on the board" — if the model
    highlights something that was never actually written, it's not
    referencing the lesson, it's fabricating content and presenting it as if
    it were already established. That's the exact failure mode this check
    exists to catch: a plausible-looking equation that the learner never saw
    getting treated as shared ground truth.
    """
    ungrounded: List[str] = []
    for step in steps:
        for event in step.get("events", []):
            if event.get("type") != "HIGHLIGHT":
                continue
            content = event.get("content")
            if not content:
                continue
            key = _normalize_math(content)
            if not _equation_already_on_board(key, known_keys):
                ungrounded.append(content)
    return ungrounded


def _format_board_state(board_state: Optional[List[str]]) -> str:
    """CURRENT_BOARD_STATE prompt block. Without this the model has no way
    to know the board isn't blank, so the HIGHLIGHT-not-WRITE rule already
    in _EVENT_SCHEMA_RULES is unenforceable."""
    if not board_state:
        return ""
    lines = "\n".join(f'  - "{expr}"' for expr in board_state)
    return (
        "\n══════════════════════════════════════\n"
        "CURRENT BOARD STATE (already visible to the learner)\n"
        "══════════════════════════════════════\n"
        f"{lines}\n"
        "If you need to refer to any of these, you MUST use HIGHLIGHT (or\n"
        "CIRCLE/UNDERLINE) — never WRITE one of them again, even while\n"
        "introducing it in a new sentence. Only WRITE an expression that is\n"
        "NOT in this list.\n"
    )


# Common English words that show up in narration leading into an equation
# ("if I have the quadratic function defined as f(x) = ...") — used to
# tell contaminated WRITE content apart from a legitimately short lead-in
# like "Let" or "So".
_WRITE_NARRATIVE_WORDS = {
    "if", "have", "the", "a", "an", "i", "we", "you", "defined", "as",
    "when", "that", "this", "with", "function", "quadratic", "linear",
    "equation", "let", "lets", "let's", "say", "consider", "suppose",
    "imagine", "now", "so", "here", "is", "are", "was", "were", "to",
    "of", "for", "and", "or", "but", "given", "where", "use", "using",
    "find", "what", "would", "will", "do", "does", "did", "look",
    "looking", "think", "know", "see",
    # Common instructional/connector words seen leading into spoken
    # equations (e.g. "in order to solve this we get x = 2") — added so
    # the Fixup 3 token-stripper can clean these too, without weakening
    # the stopping rule that keeps it from ever consuming a real equation
    # token like "2x" or a bare variable like "x".
    "in", "order", "get", "got", "getting", "can", "could", "should",
    "must", "need", "needs", "needed", "take", "taking", "solve",
    "solving", "make", "making", "put", "putting", "move", "first",
    "next", "then", "simplify", "simplifying", "combine", "combining",
    "isolate", "isolating", "both", "sides", "side", "out", "away",
    "by", "itself", "very", "algebraic", "step",
    # "write" and its inflections — narration very commonly describes the
    # act of writing notation itself ("we write y = ...", "this is written
    # as ...", "mathematicians write ..."). Missing these was the root
    # cause of literal "write y = 3x + 5" content reaching WRITE events:
    # the token-stripper would drop "we" (in the set) then immediately
    # halt on "write" (not in the set), leaving it glued to the equation.
    "write", "writes", "wrote", "written", "writing",
    # Same class of gap for near-synonyms used the same way in narration
    # ("we call this f(x)", "this is denoted y", "we name it f(x)").
    "call", "calls", "called", "denote", "denotes", "denoted",
    "name", "names", "named",
}

# Where a clean expression conventionally begins: an identifier (optionally
# with a function call like f(x)) immediately followed by "=".
_EXPR_START_RE = re.compile(r"[A-Za-z]\w*(?:\([^)]*\))?\s*=")


def _split_narrative_prefix(content: str) -> "tuple[Optional[str], str]":
    """
    Detect a WRITE event whose content has narration glued onto the front
    of the actual expression (e.g. "if I have the quadratic function
    defined as f(x) = ax^2 + bx + c") and split it into
    (full_original_sentence, bare_expression).

    Returns (None, content) when content already looks like a clean
    expression — e.g. a short/no prefix, or a prefix that isn't recognizably
    English prose (so we don't mangle legitimate short lead-ins).

    Heuristic: find the LAST "identifier(...)? =" pattern in the content —
    that's where a real expression conventionally starts. Everything before
    it is contamination only if it reads like an English sentence (several
    words, mostly drawn from a common narration vocabulary) rather than
    math notation.
    """
    matches = list(_EXPR_START_RE.finditer(content))
    if not matches:
        return None, content
    start = matches[-1].start()
    prefix = content[:start].strip()
    if not prefix:
        return None, content

    words = re.findall(r"[A-Za-z']+", prefix.lower())
    if len(words) < 3:
        return None, content  # too short to confidently call it narration
    narrative_ratio = sum(1 for w in words if w in _WRITE_NARRATIVE_WORDS) / len(words)
    if narrative_ratio < 0.4:
        return None, content

    expression = content[start:].strip()
    return content.strip(), expression


# A "bare identifier" — a lone variable with nothing else in it: no "=",
# no operators, no digits-with-a-variable. Just "x", "m", "b", or a
# subscripted "x_1" / "x_{1}". Matched against WRITE content (after
# whitespace-stripping) to catch the case where the model re-WRITEs a
# single symbol that's already part of an expression on the board instead
# of pointing at it with CIRCLE. Deliberately conservative: two-letter runs
# like "ab" don't match, because those are ambiguous (could be a genuinely
# new short constant name) in a way a single letter essentially never is
# once that exact letter has already appeared on the board.
_BARE_IDENTIFIER_RE = re.compile(r'^[A-Za-z](?:_\{?[A-Za-z0-9]+\}?)?$')


def _sanitize_steps(steps: List[Dict], prior_board_keys: Optional[set] = None) -> List[Dict]:
    """
    Safety-net post-processor. Five independent fixups:

    1. If the model put a math expression directly inside an AWAIT_RESPONSE
       event (violating the schema rules), extract it into a WRITE event
       inserted immediately before the AWAIT_RESPONSE.

    2. SPEAK-chain de-globbing. The grouping/delivery engine treats any run
       of consecutive events with sync_with_previous=True as ONE concurrent
       group and plays them word-interleaved via _interleave — that's the
       correct behavior for "WRITE while still SPEAKing" (1 SPEAK + 1 board
       action). But there is no guard upstream preventing multiple SPEAK
       events from accumulating into that same group. When the model marks
       a run of several consecutive SPEAKs as sync_with_previous: True
       (usually trying to express "smooth conversational flow" rather than
       literal simultaneity), the engine takes it literally and runs every
       SPEAK in the group concurrently, mixing their word-by-word streams
       together into garbled, mashed-together narration. We defend against
       this here by forcing sync_with_previous=False on any SPEAK event
       that immediately follows another SPEAK event, regardless of what
       the model set — SPEAK-to-SPEAK concurrency is never legitimate.

    3. Spoken-only equation backstop. The model is repeatedly observed
       introducing a brand-new example equation purely in narration while
       setting up the final probe — "say y = x² - 5x + 6, what would we
       set it to?" — and never emitting a WRITE for it, so the learner is
       asked to reason about an equation they can't actually see. We scan
       every SPEAK event for equation-shaped clauses (anything containing
       "="); if a clause never appears in any WRITE event elsewhere in the
       step, we insert a WRITE + PAUSE for it immediately after the SPEAK
       that introduced it — mirroring the "speech and a board action in
       the same breath" pattern the prompt already asks for elsewhere.

    4. Narrative-contaminated WRITE backstop. The model is observed putting
       whole sentences into a WRITE event instead of a bare expression —
       e.g. content = "if I have the quadratic function defined as
       f(x) = ax^2 + bx + c". WRITE content goes straight to a KaTeX
       renderer, which has no concept of English prose, so the entire
       string comes out as an unreadable glued-together glyph run. We
       detect this (a recognizable "identifier(...) =" expression preceded
       by several words drawn from common narration vocabulary) and split
       it: the full original sentence becomes a SPEAK event, and the WRITE
       event is trimmed down to just the bare expression that follows it.

    5. Bare-symbol WRITE downgrade. The model is observed re-WRITE-ing a
       single symbol that's already sitting inside an expression on the
       board — e.g. WRITE "y = mx + b", then separately WRITE "x", WRITE
       "y", WRITE "m", WRITE "b" — instead of CIRCLE-ing them. This is the
       same "WEAK" pattern the prompt already warns about for whole
       sub-expressions (point at what's already there instead of re-writing
       it), just at single-symbol scale, and it produces orphaned board
       entries that appear before any SPEAK has explained them. We check
       the bare identifier against every equation already on the board —
       from prior turns (prior_board_keys), from elsewhere in this same
       step (already_written), and from anything this pass has itself
       inserted (inserted_this_step) — and downgrade the event to CIRCLE
       when it matches. We also correct sync_with_previous at the same
       time: it's forced to True only when a SPEAK immediately precedes the
       event, since sync_with_previous: true paired with another board
       action (as opposed to the SPEAK right before it) isn't a supported
       combination and produces undefined playback behavior. This can't
       fully repair a WRITE that was emitted *before* the SPEAK meant to
       explain it (that's a sequencing problem, not a labeling problem —
       see the tightened prompt example instead), but it stops the bare
       symbol from appearing as fabricated new board content and stops
       the sync flag from pairing it with the wrong event.

    Operates on a shallow copy — never mutates the original steps list.

    Handles AWAIT_RESPONSE content containing MULTIPLE inline math
    expressions (e.g. "what do we get when we combine 3x and 4x?"). The
    previous version paired a single .search() (first match only) with a
    global .sub() (every match replaced) — so only the first expression
    ever reached the board, while every occurrence, including ones never
    written anywhere, got silently replaced with "that expression". The
    learner would see one orphaned WRITE and a probe question referencing
    a second expression that was never shown. This writes every distinct
    expression found, in order, before redacting.
    """
    out: List[Dict] = []
    for step in steps:
        events = step.get("events", [])

        # Pre-pass for fixup 3: collect every equation already on the board
        # ANYWHERE in this step (not just earlier than the current point —
        # a SPEAK that name-drops an equation right before its own WRITE,
        # e.g. "Imagine y = 2x² - 4x + 2." followed by WRITE 'y = 2x² - 4x + 2',
        # is the documented correct pattern and must NOT get a duplicate).
        already_written = {
            _normalize_math(e.get("content") or "")
            for e in events
            if e.get("type") == "WRITE" and e.get("content")
        } | (prior_board_keys or set())
        inserted_this_step: set = set()

        new_events: List[Dict] = []
        prev_type: Optional[str] = None
        for event in events:
            # --- Fixup 2: break SPEAK-to-SPEAK forced concurrency ---
            if event.get("type") == "SPEAK" and prev_type == "SPEAK" \
                    and event.get("sync_with_previous"):
                event = {**event, "sync_with_previous": False}

            # --- Fixup 4: split narrative-contaminated WRITE content ---
            if event.get("type") == "WRITE":
                narrative, expression = _split_narrative_prefix(event.get("content") or "")
                if narrative is not None:
                    # If a SPEAK already immediately precedes this WRITE, the
                    # narrative is almost certainly already covered there too
                    # (the model commonly speaks the full sentence, then
                    # redundantly re-dumps a near-copy of it into WRITE) —
                    # adding another SPEAK would just duplicate narration.
                    # Only insert a new SPEAK when nothing already carries it.
                    if prev_type != "SPEAK":
                        new_events.append({
                            "type": "SPEAK",
                            "content": narrative,
                            "sync_with_previous": False,
                        })
                    new_events.append({
                        **event,
                        "content": expression,
                        "sync_with_previous": True,
                    })
                    prev_type = "WRITE"
                    continue

                expression_key = _normalize_math(expression)

                # --- Fixup 5: bare-symbol WRITE downgrade ---
                # already_written spans the WHOLE step (see the pre-pass
                # comment above) and therefore always contains this very
                # event's own content — we exclude expression_key itself so
                # a symbol's first-ever appearance doesn't falsely match
                # against itself, while a genuine match against some OTHER
                # equation on the board (the actual bug case) still counts.
                combined_keys = (
                    already_written | inserted_this_step | (prior_board_keys or set())
                ) - {expression_key}
                if _BARE_IDENTIFIER_RE.match(expression.strip()) and \
                        _equation_already_on_board(expression_key, combined_keys):
                    event = {
                        **event,
                        "type": "CIRCLE",
                        "content": expression.strip(),
                        # sync_with_previous: true is only ever valid paired
                        # with the SPEAK immediately before an event — never
                        # with another board action. Re-derive it rather
                        # than trust whatever the model set.
                        "sync_with_previous": prev_type == "SPEAK",
                    }

                # downgrade WRITE -> HIGHLIGHT for cross-turn dupes ---
                # The model has no memory of prior turns' board state, so it
                # frequently re-WRITEs an equation that's already sitting on
                # the board from an earlier answer/escalation in this same
                # thread. CURRENT_BOARD_STATE asks it not to — this is the
                # backstop for when it does it anyway.
                elif prior_board_keys and _equation_already_on_board(expression_key, prior_board_keys):
                    event = { **event, "type": "HIGHLIGHT"}

            if event.get("type") != "AWAIT_RESPONSE":
                new_events.append(event)
                prev_type = event.get("type")

                # --- Fixup 3: write equations spoken but never WRITten ---
                if event.get("type") == "SPEAK":
                    for clause in _extract_equation_clauses(event.get("content") or ""):
                        # _extract_equation_clauses only strips a small, fixed
                        # set of filler lead-ins (see _EQUATION_FILLER_LEAD_RE).
                        # Anything outside that list — "we can see y = ...",
                        # "if we have 2x + 3y = 12" — would otherwise be pasted
                        # verbatim into the new WRITE event, echoing narration
                        # onto the board. _split_narrative_prefix (Fixup 4's
                        # stripper) is NOT safe to reuse here: it locates the
                        # expression start via _EXPR_START_RE, which matches
                        # only a single trailing identifier before "=" (built
                        # for single-term LHS like "f(x) = ..."). On a
                        # multi-term LHS like "2x + 3y = 12" it finds "y ="
                        # instead of the true start, truncating the equation
                        # itself into the "narrative" half and leaving a
                        # mangled WRITE like "y = 12" on the board. Instead,
                        # strip leading tokens word-by-word, only dropping a
                        # token when it's purely alphabetic AND a known
                        # narration word — the first token that isn't (e.g.
                        # "2x") halts the strip immediately, so the equation
                        # itself is never cut into.
                        clause = _strip_narrative_lead_tokens(clause)
                        key = _normalize_math(clause)
                        if _equation_already_on_board(key, already_written) \
                                or _equation_already_on_board(key, inserted_this_step):
                            continue
                        inserted_this_step.add(key)
                        new_events.append({
                            "type": "WRITE",
                            "content": clause,
                            "sync_with_previous": True,
                        })
                        new_events.append({
                            "type": "PAUSE",
                            "content": None,
                            "sync_with_previous": False,
                        })
                        prev_type = "PAUSE"
                continue

            content = event.get("content") or ""
            matches = list(_INLINE_MATH_RE.finditer(content))
            if matches:
                # Write every distinct math expression found, in order of
                # appearance, so the board shows everything the probe
                # question is about to refer to as "that expression".
                seen: set = set()
                for m in matches:
                    expr = m.group(0).strip()
                    if expr in seen:
                        continue
                    seen.add(expr)
                    new_events.append({
                        "type": "WRITE",
                        "content": expr,
                        "sync_with_previous": False,
                    })
                new_events.append({
                    "type": "PAUSE",
                    "content": None,
                    "sync_with_previous": False,
                })
                # Strip ALL matched math out of the AWAIT_RESPONSE text —
                # every occurrence now has a corresponding WRITE on the board.
                verbal = _INLINE_MATH_RE.sub("that expression", content).strip()
                new_events.append({**event, "content": verbal})
            else:
                new_events.append(event)
            prev_type = "AWAIT_RESPONSE"

        out.append({**step, "events": new_events})
    return out

# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

async def anticipate_questions(
    lesson: Dict,
    model: Optional[str] = None,
) -> Dict:
    """
    Pre-scan an entire lesson plan and generate a question bank — every
    realistic question a learner might ask at each section.

    NEW: this is meant to be launched in the BACKGROUND the instant the
    lesson starts streaming — see launch_background_anticipation() below.
    Do not await this before starting the lesson; the learner should never
    wait on question-bank generation to see their first board write.

    Returns:
      {
        "bank_id":       "uuid",
        "lesson_title":  "string",
        "subject":       "string",
        "sections": {
          "<section_id>": {
            "section_type": "...",
            "questions": [ { id, question, type, target, ... } ]
          }
        }
      }
    """
    sections = lesson.get("sections", [])
    bank: Dict[str, Any] = {
        "bank_id":      str(uuid.uuid4()),
        "lesson_title": lesson.get("lesson_title", ""),
        "subject":      lesson.get("subject", ""),
        "sections":     {},
    }

    lesson_summary = _build_lesson_summary(lesson)

    for section in sections:
        sec_id = str(section.get("id", section.get("type", "unknown")))
        prompt = (
            f"LESSON CONTEXT:\n{lesson_summary}\n\n"
            f"SECTION TO ANALYSE:\n{_format_section_context(section)}\n\n"
            f"FULL SECTION (JSON):\n{json.dumps(section, indent=2)}"
        )
        data = await _llm_json(
            _ANTICIPATE_SYSTEM, prompt,
            model=model, temperature=0.75, max_tokens=1400,
        )
        bank["sections"][sec_id] = data

    return bank


def launch_background_anticipation(
    lesson: Dict,
    model: Optional[str] = None,
) -> "asyncio.Task":
    """
    NEW — fire-and-forget background launcher.

    Call this the INSTANT generate_lesson() returns, in the same handler that
    starts streaming the lesson to the learner. Never await this call and
    never await it before the stream begins:

        lesson = await generate_lesson(...)
        bank_task = launch_background_anticipation(lesson)   # <- not awaited
        await start_streaming(lesson)                        # starts now

    Old flow:  lesson_generate → anticipate_questions → lesson_start  (serial)
    New flow:  lesson_generate → lesson_start  ‖  anticipate (background)

    Pass the returned Task straight through as `question_bank` to
    handle_answer_session() — it knows how to check `.done()` and use the
    result opportunistically without ever blocking on it.
    """
    return asyncio.create_task(anticipate_questions(lesson, model=model))


def _resolve_question_bank(question_bank: Optional[Union[Dict, "asyncio.Task"]]) -> Optional[Dict]:
    """
    Accepts either an already-finished bank dict OR the asyncio.Task returned
    by launch_background_anticipation(). Never blocks: if the task is still
    running, returns None so the caller falls through to live generation.
    """
    if question_bank is None:
        return None
    if isinstance(question_bank, asyncio.Task):
        if question_bank.done() and not question_bank.cancelled():
            try:
                return question_bank.result()
            except Exception:
                return None
        return None  # still building in the background — don't wait on it
    return question_bank


async def classify_question(
    question: str,
    active_section: Dict,
    lesson: Dict,
    model: Optional[str] = None,
) -> Dict:
    """
    Classify a learner's mid-lesson question: type, target, scope, and any
    hidden misconception lurking inside the phrasing.
    """
    prompt = (
        f'LEARNER QUESTION: "{question}"\n\n'
        f"LESSON: {_build_lesson_summary(lesson)}\n\n"
        f"ACTIVE SECTION:\n{_format_section_context(active_section)}"
    )
    return await _llm_json(
        _CLASSIFY_SYSTEM, 
        prompt, 
        model='fast', 
        temperature=0.1, 
        max_tokens=800
    )


# Generic words that show up in almost every learner question regardless of
# what it's actually about ("how did we get rid of the 4 and got 12" is
# nearly all of these). Left uncontrolled, they inflate token-overlap scores
# between two questions that share no real subject matter, so they're
# excluded before scoring a bank match.
_BANK_MATCH_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "do", "does",
    "did", "how", "why", "what", "when", "where", "which", "who", "we", "you",
    "i", "it", "this", "that", "there", "here", "and", "or", "but", "so",
    "to", "of", "for", "in", "on", "at", "with", "from", "get", "got",
    "rid", "into", "out", "again", "just", "now", "then", "one", "side",
    "other", "up", "down", "over", "back", "make", "made", "see", "know",
}


def _bank_match_is_grounded(bank_match: Dict, active_section: Optional[Dict]) -> bool:
    """
    Sanity check a bank match BEFORE trusting it as context.

    search_question_bank() scores purely on token overlap. That's cheap and
    usually fine, but two questions can share every token and still be about
    completely different math ("how did we get rid of the 4" applies equally
    to "x - 4 = 8" and "x/4 = 3"). A false-positive match hands the model a
    pre-written "target" that describes content the learner was never
    actually shown — which is exactly what makes the wrong-answer look
    authoritative instead of like a guess.

    This checks that the matched entry's target is actually anchored in the
    real section content: at least half of its distinctive tokens (numbers,
    or words 4+ characters long) must appear somewhere in the section's
    rendered text. If we can't verify that, we throw the match away rather
    than risk answering from a hallucinated or mismatched target.
    """
    if not active_section:
        return False

    target_text = str(bank_match.get("target", "") or "")
    if not target_text.strip():
        return False

    section_text = _format_section_context(active_section).lower()
    anchors = set(re.findall(r"[a-zA-Z]{4,}|\d+", target_text.lower()))
    anchors -= _BANK_MATCH_STOPWORDS
    if not anchors:
        return False

    hits = sum(1 for a in anchors if a in section_text)
    return (hits / len(anchors)) >= 0.5


def search_question_bank(
    question: str,
    bank: Dict,
    active_section_id: str,
    active_section: Optional[Dict] = None,
    similarity_threshold: float = 0.72,
) -> Optional[Dict]:
    """
    Look for a pre-anticipated question in the bank that closely matches what
    the learner just asked. Uses simple token overlap (no embedding call
    needed), with generic filler words stripped out first so two unrelated
    questions can't match purely on shared stopwords ("how", "did", "get",
    "rid", "the", ...).

    If `active_section` is provided, a match is additionally required to be
    grounded in the real section content (see _bank_match_is_grounded) before
    it's returned — this is what stops a stray high-overlap match from a
    DIFFERENT part of the lesson from being surfaced as if it were about the
    content the learner is currently looking at.
    """
    question_tokens = set(re.findall(r"\w+", question.lower())) - _BANK_MATCH_STOPWORDS
    if len(question_tokens) < 2:
        return None

    section_bank = bank.get("sections", {}).get(active_section_id, {})
    anticipated = section_bank.get("questions", [])

    best_match: Optional[Dict] = None
    best_score: float = 0.0

    for anticipated_q in anticipated:
        # Defensive: anticipate_questions() stores raw LLM JSON with no
        # schema validation (unlike lesson_engine.py's
        # _validate_lesson_schema), so a single deviation from the
        # documented {id, question, type, target, ...} object shape —
        # e.g. the model returning a bare string for one entry — used to
        # crash the entire /answer/ask request with an opaque
        # "'str' object has no attribute 'get'" three calls away from
        # here. Skip and log instead of letting one bad bank entry take
        # down a live question.
        if not isinstance(anticipated_q, dict):
            logger.warning(
                "search_question_bank: skipping malformed bank entry "
                "(section_id=%s) — expected a question object, got "
                "%s=%r",
                active_section_id, type(anticipated_q).__name__, anticipated_q,
            )
            continue
        candidate_tokens = set(
            re.findall(r"\w+", anticipated_q.get("question", "").lower())
        ) - _BANK_MATCH_STOPWORDS
        if not candidate_tokens:
            continue
        overlap = question_tokens & candidate_tokens
        score = len(overlap) / max(len(question_tokens), len(candidate_tokens))
        if score > best_score:
            best_score = score
            best_match = anticipated_q

    if best_score < similarity_threshold or best_match is None:
        return None

    if active_section is not None and not _bank_match_is_grounded(best_match, active_section):
        logger.warning(
            "search_question_bank: discarding ungrounded bank match "
            "(section_id=%s, score=%.2f, target=%r) — target not found in "
            "active section content",
            active_section_id, best_score, best_match.get("target"),
        )
        return None

    return best_match


async def answer_learner_question(
    question: str,
    active_section: Dict,
    lesson: Dict,
    resume_pointer: Optional[Dict] = None,
    conversation_history: Optional[List[Dict]] = None,
    examples_given: int = 0,
    bank_match: Optional[Dict] = None,
    board_state: Optional[list[str]] = None,
    model: Optional[str] = None,
) -> Dict:
    """
    Generate a full, teacher-voice answer to a learner's mid-lesson question,
    emitted as SPEAK/WRITE/PAUSE/AWAIT_RESPONSE steps (lesson_engine schema).

    Returns:
      {
        "session_id":           "uuid",
        "question_rephrased":   "...",
        "question_type":        "WHY | ...",
        "hidden_misconception": "... | null",
        "scope":                "in_lesson | ...",
        "approach_used":        "ALGEBRAIC | ...",
        "steps":                [ ... ],            # raw steps, for callers that need them
        "envelope":             { type, question, resume, sections },  # ready to send to frontend
        "probe_question":       "the literal AWAIT_RESPONSE text, for grading the next reply",
        "examples_given":       1,
        "understanding_status": "PENDING",
        "approaches_used":      ["ALGEBRAIC"]
      }
    """
    if not isinstance(active_section, dict):
        raise TypeError(
            "answer_learner_question: active_section must be a resolved "
            f"section dict, got {type(active_section).__name__}={active_section!r}. "
            "This almost always means the caller passed a raw segment id/"
            "pause_context value (e.g. 'sec_worked_1') instead of looking "
            "it up against the lesson's sections first — check the "
            "active_segment-mismatch fallback path in the router."
        )

    classification = await classify_question(question, active_section, lesson, model)
    approach = _select_next_approach(examples_given)

    misconception_note = ""
    if classification.get("hidden_misconception"):
        misconception_note = (
            f"\n⚠ MISCONCEPTION DETECTED: {classification['hidden_misconception']}\n"
            "IMPORTANT: Address and gently correct this BEFORE answering the surface "
            "question. Never make them feel foolish for it.\n"
        )

    scope_note = ""
    scope = classification.get("scope", "in_lesson")
    if scope == "prerequisite_gap":
        scope_note = (
            "\n⚠ PREREQUISITE GAP: This question suggests missing background knowledge. "
            "Give a 1-sentence bridge to fill the gap, then answer.\n"
        )
    elif scope == "out_of_scope":
        scope_note = (
            "\n⚠ OUT OF SCOPE: Outside this lesson. Answer in one sentence, then redirect "
            "warmly to the current lesson.\n"
        )

    bank_note = ""
    if bank_match:
        bank_note = (
            f"\nBANK MATCH CONTEXT: This question was anticipated. "
            f"Target: {bank_match.get('target', '')}. "
            f"Type: {bank_match.get('type', '')}. "
            f"Hidden misconception (if any): {bank_match.get('hidden_misconception', 'none')}.\n"
        )

    history_note = ""
    if conversation_history:
        recent = conversation_history[-4:]
        history_note = f"\nRECENT CONVERSATION:\n{json.dumps(recent, indent=2)}\n"

    prompt = (
        f'LEARNER QUESTION: "{question}"\n'
        f'REAL QUESTION (rephrased): "{classification.get("rephrased", question)}"\n'
        f"QUESTION TYPE: {classification.get('question_type', 'GENERAL')}\n"
        f"TEACHING APPROACH TO USE: {approach}\n"
        f"{misconception_note}"
        f"{scope_note}"
        f"{bank_note}"
        f"\nACTIVE SECTION:\n{_format_section_context(active_section)}\n"
        f"\nLESSON CONTEXT:\n{_build_lesson_summary(lesson)}\n"
        f"{history_note}"
            f"{_format_board_state(board_state)}"
    )

    result = await _llm_json(
        # 0.7 -> 0.4: this call's output is judged almost entirely on
        # structural consistency (correct WRITE vs CIRCLE choice, correct
        # sync_with_previous pairing) rather than creative wording. 0.4
        # matches the temperature already used for the correction retry
        # below and lesson_engine.py's single big generation call (0.3) —
        # high temperature on a format-sensitive task increases drift away
        # from the few-shot examples' pattern, which is exactly the kind
        # of mistake Fixup 5 above exists to catch after the fact.
        # 2500 -> 3500: _ANSWER_SYSTEM's mandatory content now requires a
        # FRESH, separate worked example (not a reuse of the board's
        # in-progress equation) on top of the reconnect/explanation/probe —
        # a full extra mini-example's worth of SPEAK/WRITE/PAUSE events plus
        # an explicit bridge-back sentence. That's routinely running past
        # the old 2500 ceiling and hitting truncation. 3500 gives headroom
        # for two full examples instead of one.
        _ANSWER_SYSTEM, prompt, model=model, temperature=0.4, max_tokens=3500
    )
    steps = result.get("steps", [])
    steps = _sanitize_steps(
        steps,
        prior_board_keys={
            _normalize_math(s)
            for s in (board_state or [])
        }
    )
    approach_used = result.get("approach_used", approach)
    core_explanation = result.get("core_explanation")

    # ── GROUNDING CHECK ──────────────────────────────────────────────────
    # Everything the model HIGHLIGHTs should be something the learner has
    # actually already seen. If it isn't, the model has fabricated an
    # equation and is presenting it as pre-existing lesson content — give
    # it one chance to self-correct with the mismatch spelled out, then
    # fall back to a safe downgrade if it still doesn't line up.
    # Grounding is checked strictly against board_state — the field that's
    # actually maintained turn-by-turn from real WRITE events via
    # _merge_board_state — rather than active_section's full step list.
    # active_section is the section's *plan* (routes.py's
    # _resolve_active_section trims it to steps actually delivered before
    # the pause when it can, but that's a best-effort guard, not a
    # guarantee — e.g. the no-session_id / no-pause_context fallback
    # returns the client-supplied section untrimmed). board_state has no
    # such gap: it only ever contains what a WRITE event actually put on
    # the board, so it's the one source of truth this check can't afford
    # to loosen.
    known_keys = {
        _normalize_math(s) for s in (board_state or [])
    }

    # Detection-only check for a new hypothetical value smuggled into
    # AWAIT_RESPONSE content instead of being WRITten first (e.g. "...if the
    # rise doubled to 16?"). Doesn't trigger a retry — see
    # _find_ungrounded_probe_numbers for why an auto-fix here isn't safe —
    # but logs loudly so it shows up the same way ungrounded HIGHLIGHTs do.
    probe_known_text = " ".join(board_state or [])
    for step in steps:
        for event in step.get("events", []):
            if event.get("type") == "WRITE" and event.get("content"):
                probe_known_text += " " + event["content"]
    ungrounded_numbers = _find_ungrounded_probe_numbers(steps, probe_known_text)
    if ungrounded_numbers:
        logger.warning(
            "answer_learner_question: AWAIT_RESPONSE references a value "
            "not found anywhere on the board (question=%r, "
            "ungrounded_numbers=%r) — schema violation, not auto-corrected",
            question, ungrounded_numbers,
        )

    ungrounded = _find_ungrounded_highlights(steps, known_keys)
    if ungrounded:
        logger.warning(
            "answer_learner_question: HIGHLIGHT referenced content not "
            "found in active section or board_state (question=%r, "
            "ungrounded=%r) — retrying once with correction",
            question, ungrounded,
        )
        correction_note = (
            "\n⚠ YOUR PREVIOUS ATTEMPT REFERENCED CONTENT THAT WAS NEVER "
            "SHOWN TO THE LEARNER: "
            f"{', '.join(repr(u) for u in ungrounded)}. "
            "You MUST ground your answer strictly in the equations that "
            "literally appear in ACTIVE SECTION / CURRENT BOARD STATE above "
            "— do not invent a similar-looking equation. If you need a new "
            "example to illustrate the idea, introduce it explicitly with "
            "WRITE (never HIGHLIGHT something that isn't already there).\n"
        )
        # The retry itself can hit the same truncation failure mode as the
        # original call — a longer prompt (correction_note appended) still
        # has to regenerate a full answer, now at the same 3500-token
        # baseline as the primary call above (bumped from 2500 for the
        # mandatory second/fresh-example requirement) plus its own headroom
        # for the correction note. Keep the same +1500 margin the original
        # 2500->4000 retry had, scaled to the new baseline: 3500->5000.
        # _llm_json raises a bare RuntimeError on truncation, and previously
        # nothing here caught it, so it propagated straight through
        # answer_learner_question -> handle_answer_session -> routes.py as
        # an uncaught 500. Treat a failed retry the same way we already
        # treat a retry that merely came back still-ungrounded: fall
        # through to the downgrade-to-WRITE safety net below instead of
        # crashing.
        retry_steps = None
        try:
            retry_result = await _llm_json(
                _ANSWER_SYSTEM, prompt + correction_note, model=model,
                temperature=0.4, max_tokens=5000,
            )
            retry_steps = _sanitize_steps(
                retry_result.get("steps", []),
                prior_board_keys={_normalize_math(s) for s in (board_state or [])},
            )
        except RuntimeError:
            logger.error(
                "answer_learner_question: correction retry itself failed "
                "(question=%r) — falling back to downgrading original "
                "HIGHLIGHT events to WRITE instead of raising",
                question,
            )

        if retry_steps is not None and not _find_ungrounded_highlights(retry_steps, known_keys):
            steps = retry_steps
            approach_used = retry_result.get("approach_used", approach_used)
            core_explanation = retry_result.get("core_explanation", core_explanation)
        else:
            # Still not grounded (or the retry failed outright) — don't
            # silently ship a fabricated "this is already on the board"
            # claim, and don't crash the request either. Downgrade to
            # WRITE so it's at least honestly framed as new content being
            # introduced now, and keep the warning loud in the logs for
            # follow-up.
            logger.error(
                "answer_learner_question: retry still ungrounded "
                "(question=%r) — downgrading HIGHLIGHT events to WRITE",
                question,
            )
            for step in steps:
                for event in step.get("events", []):
                    if event.get("type") == "HIGHLIGHT" and event.get("content") \
                            and not _equation_already_on_board(
                                _normalize_math(event["content"]), known_keys
                            ):
                        event["type"] = "WRITE"

    envelope = _wrap_answer_envelope(
        question=question,
        resume_pointer=resume_pointer,
        steps=steps,
        section_type="ANSWER_EXPLANATION",
        title=f"Answering: {classification.get('rephrased', question)[:60]}",
        purpose="Resolve the learner's mid-lesson question before resuming.",
    )

    return {
        "session_id":           str(uuid.uuid4()),
        "question_rephrased":   classification.get("rephrased", question),
        "question_type":        classification.get("question_type", "GENERAL"),
        "hidden_misconception": classification.get("hidden_misconception"),
        "scope":                scope,
        "approach_used":        approach_used,
        "steps":                steps,
        "board_state":          _merge_board_state(board_state, steps),
        "envelope":             envelope,
        "probe_question":       _extract_probe_question(steps),
        "examples_given":       1,
        "understanding_status": UnderstandingStatus.PENDING,
        "approaches_used":      [approach_used],
        "grounding_warning":    bool(ungrounded),
        "core_explanation":     core_explanation,
    }


async def classify_understanding(
    learner_response: str,
    question: str,
    examples_given: int = 1,
    probe_question: Optional[str] = None,
    conversation_history: Optional[List[Dict]] = None,
    model: Optional[str] = None,
) -> Dict:
    """
    Read a learner's reply after an explanation and determine, via the LLM
    agent (no keyword list), whether they have genuinely understood — and,
    if `probe_question` is supplied, whether their reply is itself a direct
    (correct/partial/incorrect) attempt at answering it.

    `conversation_history` is passed through purely so the acknowledgment
    text doesn't go stale — without it this call has no way of knowing it
    already said "Exactly right!" three turns ago and will keep reaching
    for the same one or two example phrases from its own system prompt
    verbatim, which reads as robotic/hardcoded over a real conversation.

    Blank input short-circuits to PENDING without an LLM call — this is a
    pure emptiness check, not phrase matching, and exists so the timeout
    policy in handle_answer_session() can tell "no reply yet" apart from
    "replied with something ambiguous".

    After MAX_EXAMPLES_BEFORE_PROBE, automatically escalates status to
    ESCALATED if not yet confirmed.

    Returns:
      {
        "status":             "CONFIRMED | UNCERTAIN | NOT_CONFIRMED | PENDING",
        "confidence":         float,
        "detected_signals":   [...],
        "recommendation":     "RESUME_LESSON | GIVE_EXAMPLE | PROBE_SPECIFIC | SIMPLIFY | WAIT",
        "follow_on_question": "extracted follow-up question, or null",
        "probe_evaluation": {
          "was_answer_attempt": bool,
          "correctness":        "CORRECT | PARTIAL | INCORRECT | NOT_APPLICABLE",
          "acknowledgment":      "short spoken acknowledgment, or ''"
        }
      }
    """
    if _is_blank(learner_response):
        return {
            "status":             UnderstandingStatus.PENDING,
            "confidence":         1.0,
            "detected_signals":   ["empty or minimal response"],
            "recommendation":     "WAIT",
            "follow_on_question": None,
            "probe_evaluation": {
                "was_answer_attempt": False,
                "correctness":        ProbeOutcome.NOT_APPLICABLE,
                "acknowledgment":     "",
            },
        }

    probe_block = (
        f'THE PROBE QUESTION JUST ASKED: "{probe_question}"\n'
        "If the learner's reply reads as a direct attempt to answer THIS "
        "question, grade it in probe_evaluation.\n\n"
        if probe_question else
        "No specific probe question was tracked for this turn — set "
        "probe_evaluation.was_answer_attempt to false unless the reply is "
        "unmistakably answering a math question.\n\n"
    )

    history_block = ""
    if conversation_history:
        recent = conversation_history[-6:]
        history_block = (
            f"\nRECENT CONVERSATION (check this for acknowledgment phrases "
            f"you already used — your new acknowledgment must be worded "
            f"differently from any of these, even if the situation is "
            f"similar):\n{json.dumps(recent, indent=2)}\n"
        )

    prompt = (
        f'ORIGINAL QUESTION: "{question}"\n'
        f"EXAMPLES GIVEN SO FAR: {examples_given}\n"
        f"{probe_block}"
        f"{history_block}"
        f'LEARNER\'S REPLY:\n"{learner_response}"'
    )
    result = await _llm_json(
        _UNDERSTAND_SYSTEM, prompt, model=model, temperature=0.1, max_tokens=800
    )

    # Defensive default if the model omits probe_evaluation entirely.
    result.setdefault("probe_evaluation", {
        "was_answer_attempt": False,
        "correctness":        ProbeOutcome.NOT_APPLICABLE,
        "acknowledgment":     "",
    })

    # A correctly-answered probe is a confirmation signal even if the model
    # was conservative on `status` — let the probe grading win when explicit.
    if result["probe_evaluation"].get("correctness") == ProbeOutcome.CORRECT:
        result["status"] = UnderstandingStatus.CONFIRMED
        result["recommendation"] = "RESUME_LESSON"
    elif result["probe_evaluation"].get("correctness") == ProbeOutcome.INCORRECT:
        result["status"] = UnderstandingStatus.NOT_CONFIRMED
        result["recommendation"] = "GIVE_EXAMPLE"

    # If we've hit the example ceiling and still not confirmed, force a probe
    if (
        examples_given >= MAX_EXAMPLES_BEFORE_PROBE
        and result.get("status") != UnderstandingStatus.CONFIRMED
    ):
        result["status"]         = UnderstandingStatus.ESCALATED
        result["recommendation"] = "PROBE_SPECIFIC"

    return result


async def escalate_with_example(
    question: str,
    active_section: Dict,
    lesson: Dict,
    resume_pointer: Optional[Dict] = None,
    conversation_history: Optional[List[Dict]] = None,
    example_number: int = 1,
    previous_approach: str = APPROACH_PROGRESSION[0],
    wrong_answer_note: Optional[str] = None,
    probe_question: Optional[str] = None,
    model: Optional[str] = None,
    board_state: Optional[List[str]] = None,
) -> Dict:
    """
    Generate a fresh explanation using a completely different teaching approach.
    Called when classify_understanding() returns NOT_CONFIRMED or UNCERTAIN —
    including the case where the learner answered the probe INCORRECTLY, in
    which case `wrong_answer_note` should describe what they answered so the
    new explanation can respond to their specific mistake.

    `probe_question` is the literal text of whatever AWAIT_RESPONSE prompt the
    learner was just replying to (or staying silent on). It is passed through
    so the new example can stay anchored to any specific numbers that probe
    already pinned down (e.g. "we kept 'a' at 4") — without it, the model has
    no way to know those numbers were already on the table and may invent a
    fresh, disconnected example instead of bridging from the one in progress.

    Returns:
      {
        "escalation_number":   int,
        "approach_used":       "ANALOGY | ...",
        "steps":               [ ... ],
        "envelope":            { type, question, resume, sections },
        "probe_question":       "the literal AWAIT_RESPONSE text for next-turn grading",
        "examples_given":       int,
        "understanding_status": "PENDING"
      }
    """
    required_approach = _select_next_approach(example_number, previous_approach)

    wrong_answer_block = ""
    if wrong_answer_note:
        probe_line = (
            f'\nTHE PROBE THEY WERE ANSWERING: "{probe_question}"\n'
            if probe_question else ""
        )
        wrong_answer_block = (
            f"{probe_line}"
            f"\nLEARNER'S INCORRECT ATTEMPT: \"{wrong_answer_note}\"\n"
            "Open by acknowledging this specific attempt — name what they said.\n"
            "If the probe above already pinned down specific numbers, your new "
            "example MUST reuse those same numbers (see rule 3b) — do not "
            "substitute different values for the same variables.\n"
        )
    elif probe_question:
        wrong_answer_block = (
            f'\nPREVIOUS PROBE QUESTION (learner went quiet / no clear reply): '
            f'"{probe_question}"\n'
            "If this already pinned down specific numbers, reuse those same "
            "numbers in your new example (see rule 3b).\n"
        )

    recent_history = json.dumps((conversation_history or [])[-6:], indent=2)

    prompt = (
        f'LEARNER QUESTION: "{question}"\n'
        f"ESCALATION ATTEMPT #{example_number + 1}\n"
        f"Previous approach: {previous_approach}  →  New approach required: {required_approach}\n"
        f"{wrong_answer_block}\n"
        f"ACTIVE SECTION:\n{_format_section_context(active_section)}\n\n"
        f"LESSON CONTEXT:\n{_build_lesson_summary(lesson)}\n\n"
        f"RECENT CONVERSATION:\n{recent_history}"
            f"{_format_board_state(board_state)}"
    )
    result = await _llm_json(
        _ESCALATE_SYSTEM, prompt, model=model, temperature=0.75, max_tokens=1400
    )
    steps = result.get("steps", [])
    steps = _sanitize_steps(
        steps,
        prior_board_keys={
            _normalize_math(s)
            for s in (board_state or [])
        }
    ) 
    approach_used = result.get("approach_used", required_approach)
    core_explanation = result.get("core_explanation")

    envelope = _wrap_answer_envelope(
        question=question,
        resume_pointer=resume_pointer,
        steps=steps,
        section_type="ANSWER_ESCALATION",
        title=f"Another way to see it ({approach_used.title() if isinstance(approach_used, str) else approach_used})",
        purpose="Re-explain using a different teaching approach after the first attempt didn't land.",
    )

    return {
        "escalation_number":    example_number,
        "approach_used":        approach_used,
        "steps":                steps,
        "board_state":          _merge_board_state(board_state, steps),
        "envelope":             envelope,
        "probe_question":       _extract_probe_question(steps),
        "examples_given":       example_number + 1,
        "understanding_status": UnderstandingStatus.PENDING,
        "core_explanation":     core_explanation,
    }


async def probe_confusion_point(
    question: str,
    active_section: Dict,
    lesson: Dict,
    resume_pointer: Optional[Dict] = None,
    examples_given: int = 0,
    model: Optional[str] = None,
) -> Dict:
    """
    Called when MAX_EXAMPLES_BEFORE_PROBE has been reached and understanding
    is still not confirmed. Asks a targeted diagnostic question instead of
    yet another example. The response is then passed into
    generate_micro_explanation() for a surgical fix.
    """
    prompt = (
        f'QUESTION THE LEARNER ASKED: "{question}"\n'
        f"DIFFERENT EXPLANATIONS GIVEN: {examples_given}\n\n"
        f"SECTION:\n{_format_section_context(active_section)}\n\n"
        f"LESSON: {_build_lesson_summary(lesson)}"
    )
    result = await _llm_json(
        _PROBE_SYSTEM, 
        prompt, 
        model='fast', 
        temperature=0.3, 
        max_tokens=600
    )
    steps = result.get("steps", [])
    steps = _sanitize_steps(steps) 

    envelope = _wrap_answer_envelope(
        question=question,
        resume_pointer=resume_pointer,
        steps=steps,
        section_type="ANSWER_PROBE",
        title="Locating exactly where this got confusing",
        purpose="Find the precise point where understanding broke down.",
    )

    return {
        "type":                 "CONFUSION_PROBE",
        "examples_given":       examples_given,
        "steps":                steps,
        "envelope":             envelope,
        "probe_question":       _extract_probe_question(steps),
        "what_answer_reveals":  result.get("what_answer_reveals", {}),
        "understanding_status": UnderstandingStatus.ESCALATED,
    }


async def generate_micro_explanation(
    confusion_location: str,
    question: str,
    active_section: Dict,
    lesson: Dict,
    resume_pointer: Optional[Dict] = None,
    model: Optional[str] = None,
    board_state: Optional[List[str]] = None
) -> Dict:
    """
    After probe_confusion_point() has identified WHERE the learner is lost,
    generate a laser-focused micro-explanation that addresses only that point.
    """
    prompt = (
        f'ORIGINAL QUESTION: "{question}"\n'
        f'WHERE THE LEARNER GOT LOST: "{confusion_location}"\n\n'
        f"SECTION:\n{_format_section_context(active_section)}\n\n"
        f"LESSON: {_build_lesson_summary(lesson)}\n\n"
        "Your job: a 2–4 sentence surgical fix for ONLY this one point. "
        "Then one confirming probe to verify it landed."
        f"{_format_board_state(board_state)}"
    )
    result = await _llm_json(
        _MICRO_SYSTEM, 
        prompt, 
        model='fast', 
        temperature=0.5, 
        max_tokens=1000
    )
    steps = result.get("steps", [])
    steps = _sanitize_steps(
        steps,
        prior_board_keys={
            _normalize_math(s)
            for s in (board_state or [])
        }
    )

    envelope = _wrap_answer_envelope(
        question=question,
        resume_pointer=resume_pointer,
        steps=steps,
        section_type="ANSWER_MICRO_FIX",
        title="Fixing that exact point",
        purpose="Surgical fix for the precise moment comprehension broke down.",
    )

    return {
        "type":                 "MICRO_EXPLANATION",
        "confusion_at":         confusion_location,
        "steps":                steps,
        "board_state":          _merge_board_state(board_state, steps),
        "envelope":             envelope,
        "probe_question":       _extract_probe_question(steps),
        "understanding_status": UnderstandingStatus.PENDING,
        "core_explanation":     result.get("core_explanation"),
    }


_GENERIC_CHECK_QUESTION = (
    "Does that make sense — feeling good about how we got there, "
    "or want to go over it once more?"
)


async def _generate_confirmation_check_question(
    question: str,
    active_section: Dict,
    lesson: Dict,
    acknowledgment: str,
    model: Optional[str] = None,
) -> str:
    """
    Ask the LLM for a one-sentence, concept-specific "do you really get it"
    check, grounded in the actual probe/concept just discussed, rather than
    a generic "does that make sense?" every time. Falls back to the generic
    phrasing on any parse failure or empty result so this step never blocks
    the flow.
    """
    prompt = (
        f'LEARNER QUESTION: "{question}"\n'
        f'ACKNOWLEDGMENT JUST SPOKEN: "{acknowledgment}"\n\n'
        f"SECTION:\n{_format_section_context(active_section)}\n\n"
        f"LESSON: {_build_lesson_summary(lesson)}"
    )
    result = await _llm_json(
        _CONFIRM_CHECK_SYSTEM,
        prompt, 
        model='fast', 
        temperature=0.5, 
        max_tokens=200
    )
    check_question = result.get("check_question")
    if not check_question or not isinstance(check_question, str) or _is_blank(check_question):
        return _GENERIC_CHECK_QUESTION
    return check_question.strip()


async def _build_confirmation_check_result(
    question: str,
    active_section: Dict,
    lesson: Dict,
    resume_pointer: Optional[Dict],
    acknowledgment: str,
    examples_given: int,
    used_approaches: List[str],
    timeout_grace_used: bool,
    board_state: Optional[List[str]],
    core_explanation: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict:
    """
    A learner just answered a probe CORRECTLY. That confirms they got ONE
    answer right — it does not by itself confirm the underlying concept
    landed. Rather than resume the lesson on the spot, let them down slowly:
    speak the acknowledgment (e.g. "Yes! The answer there is 2x."), then ask
    one soft, low-pressure, CONCEPT-SPECIFIC check for real understanding
    (generated fresh per-turn — see _generate_confirmation_check_question),
    ending in a fresh AWAIT_RESPONSE. The lesson resumes only once THAT
    check comes back confirmed — see the `awaiting_final_confirmation`
    branch in handle_answer_session for the other half of this loop.
    """
    check_question = await _generate_confirmation_check_question(
        question=question,
        active_section=active_section,
        lesson=lesson,
        acknowledgment=acknowledgment,
        model=model,
    )

    events: List[Dict] = []
    if acknowledgment:
        events.append(_make_speak_event(acknowledgment))
    events.append({
        "type": "SPEAK",
        "content": check_question,
        "sync_with_previous": False,
    })
    events.append({
        "type": "AWAIT_RESPONSE",
        "content": check_question,
        "sync_with_previous": False,
    })

    envelope = _wrap_answer_envelope(
        question=question,
        resume_pointer=resume_pointer,
        steps=[{
            "id": "confirmation_check_step",
            "objective": "Confirm real understanding before resuming the lesson",
            "events": events,
        }],
        section_type="ANSWER_CONFIRMATION_CHECK",
        title="Checking it landed",
        purpose="Confirm the learner understands the concept, not just the single probe answer, before resuming.",
    )

    return {
        "action":                      "ANSWER",  # in STREAMABLE_ACTIONS → gets spoken
        "payload":                     envelope,
        "examples_given":              examples_given,
        # Confirmed on the probe, not yet on the concept as a whole — keep
        # status short of CONFIRMED so nothing downstream mistakes this for
        # a green light to resume.
        "understanding_status":        UnderstandingStatus.UNCERTAIN,
        "approaches_used":             used_approaches,
        "probe_question":              check_question,
        "timeout_grace_used":          timeout_grace_used,
        "resume_lesson":               False,
        "awaiting_final_confirmation": True,
        "board_state":                 board_state or [],
        "core_explanation":            core_explanation,
    }


# ─────────────────────────────────────────────────────────────────────────────
# ORCHESTRATOR
# ─────────────────────────────────────────────────────────────────────────────
async def handle_answer_session(
    question:             str,
    active_section:       Dict,
    lesson:               Dict,
    resume_pointer:        Optional[Dict]             = None,
    learner_response:      Optional[str]               = None,
    conversation_history:  Optional[List[Dict]]        = None,
    examples_given:        int                         = 0,
    previous_approach:     Optional[str]               = None,
    approaches_used:       Optional[List[str]]         = None,
    question_bank:          Optional[Union[Dict, "asyncio.Task"]] = None,
    confusion_location:     Optional[str]               = None,
    probe_question:         Optional[str]               = None,
    seconds_since_prompt:   Optional[float]             = None,
    timeout_grace_used:     bool                        = False,
    timeout_seconds:        float                       = CONFIRMATION_TIMEOUT_SECONDS,
    board_state:            Optional[List[str]]         = None,
    awaiting_final_confirmation: bool                   = False,
    core_explanation:       Optional[str]                         = None,
    model:                  Optional[str]                         = None,
) -> Dict:
    """
    ═══════════════════════════════════════════════════════════════
    PRIMARY ENDPOINT HANDLER — manages the full Q&A lifecycle.
    ═══════════════════════════════════════════════════════════════

    The frontend calls this on every turn of a learner question interaction.
    The function inspects the current state and calls the appropriate engine
    function, returning a consistent response envelope.

    ── TURN 1 (initial question) ────────────────────────────────
    Pass:  question, active_section, lesson, resume_pointer
    Leave: learner_response = None  (default)

    ── TURN 2+ (learner replied, or we're checking for a timeout) ──
    Pass:  question, active_section, lesson, resume_pointer,
           learner_response    = "..." (or None/"" if checking timeout only),
           examples_given      = (from previous response),
           previous_approach   = (from previous response),
           approaches_used     = (from previous response),
           probe_question      = (from previous response — needed to grade
                                   a direct attempt at the probe),
           seconds_since_prompt= wall-clock seconds since that probe fired,
           timeout_grace_used  = (from previous response),
           board_state         = (from previous response — see below)

    ── AFTER PROBE (learner located confusion) ─────────────────
    Pass:  same as Turn 2+, plus:
           confusion_location = learner's response to the probe question

    ── FINAL CONFIRMATION CHECK (new) ───────────────────────────
    A correctly-answered AWAIT_RESPONSE probe is evidence the learner got
    ONE answer right — it is not, by itself, proof the underlying concept
    landed. So a CORRECT probe grading no longer resumes the lesson on the
    spot. Instead this engine "lets them down slowly": it speaks the
    acknowledgment (e.g. "Yes! The answer there is 2x.") and then asks one
    soft, low-pressure check — "Does that make sense, or want to go over
    it once more?" — as a fresh AWAIT_RESPONSE. The response envelope for
    that turn comes back with `awaiting_final_confirmation: true` and
    `resume_lesson: false`. The frontend stores that flag exactly like
    timeout_grace_used and passes it straight back on the NEXT call along
    with the learner's reply to the soft check:
           awaiting_final_confirmation = True,
           learner_response            = "...",
           probe_question              = (from previous response — the
                                            soft check text itself)
    The lesson only actually resumes (`resume_lesson: true`) once that
    reply reads as real confirmation. If the learner instead asks another
    question at that point, it's answered as a normal follow-on and the
    same confirmation loop re-arms once that new thread wraps up. If they
    say they're still not sure, one more explanation is given instead of
    forcing them back into the lesson on a false-positive confirmation.

    ── BOARD STATE ───────────────────────────────────────────────
    board_state is the running list of every expression that has been
    WRITten to the board across this entire Q&A thread (not the main
    lesson's own board state — just what this engine has put up). It's
    threaded into every prompt as CURRENT_BOARD_STATE so the model reaches
    for HIGHLIGHT instead of silently re-WRITE-ing the same equation under
    a new sentence each turn, and _sanitize_steps uses it as a hard
    backstop (downgrades any WRITE that duplicates board_state into a
    HIGHLIGHT) in case the model ignores the prompt instruction anyway.
    Frontend stores it and passes it back next turn, same as
    examples_given / approaches_used.

    ── RESPONSE ENVELOPE ────────────────────────────────────────
    {
      "action":               "ANSWER | ESCALATE | PROBE | MICRO | RESUME",
      "payload":              { type, question, resume, sections, ... },
      "examples_given":       int,
      "understanding_status": "PENDING | CONFIRMED | ESCALATED | ...",
      "approaches_used":      ["ALGEBRAIC", "ANALOGY", ...],
      "probe_question":       "literal AWAIT_RESPONSE text, or null",
      "timeout_grace_used":   bool,
      "resume_lesson":        bool,   — true only once real understanding is
                                        confirmed (see FINAL CONFIRMATION
                                        CHECK above) or the session timed out
      "awaiting_final_confirmation": bool,  — true when this turn's payload
                                        IS the soft "does that make sense"
                                        check; pass it straight back with
                                        the learner's reply next call
      "board_state":          ["f(x) = ax^2 + bx + c", ...]
    }

    The frontend stores examples_given, approaches_used, previous_approach,
    probe_question, timeout_grace_used, and board_state in session state and
    passes them back on each subsequent call. It also tracks wall-clock time
    and computes seconds_since_prompt itself — this engine has no notion of
    real time.
    ═══════════════════════════════════════════════════════════════
    """
    conv_history    = conversation_history or []
    used_approaches = approaches_used or []
    bank            = _resolve_question_bank(question_bank)
    # Tracks the most recent substantive explanation across this whole Q&A
    # thread. Starts as whatever the frontend passed back in (the value from
    # the previous turn's response), and gets overwritten only when a call
    # in this turn actually produces a fresh one (answer/escalate/micro).
    # Every return path below carries this forward so the frontend always
    # has real content to hand to the resume bridge — see _RESUME_BRIDGE_SYSTEM
    # in streaming_engine.py, which needs this to avoid a contextless resume.
    current_core_explanation = core_explanation

    # ── FINAL CONFIRMATION CHECK: learner replied to the soft "does that
    # make sense" check that follows a correctly-answered probe ─────────────
    # This is the other half of _build_confirmation_check_result(). A
    # correct probe answer alone no longer resumes the lesson — it lands
    # here first, and ONLY a genuinely-confirmed reply to this soft check
    # actually resumes the lesson.
    if awaiting_final_confirmation:
        # Silence on this low-stakes check still obeys the same timeout
        # policy as everywhere else — we don't hold the learner hostage.
        if (
            _is_blank(learner_response)
            and seconds_since_prompt is not None
            and seconds_since_prompt >= timeout_seconds
        ):
            return {
                "action": "RESUME",
                "payload": {
                    "message": "Learner did not respond to the confirmation check. Resuming the lesson.",
                    "reason":  "timeout",
                    "resume":  resume_pointer,
                },
                "examples_given":              examples_given,
                "understanding_status":        UnderstandingStatus.CONFIRMED,
                "approaches_used":             used_approaches,
                "probe_question":              None,
                "timeout_grace_used":          timeout_grace_used,
                "resume_lesson":               True,
                "awaiting_final_confirmation": False,
                "board_state":                 board_state or [],
                "core_explanation":            current_core_explanation,
            }

        understanding  = await classify_understanding(
            learner_response=learner_response,
            question=question,
            examples_given=examples_given,
            probe_question=probe_question,  # the soft check question text
            conversation_history=conv_history,
            model=model,
        )
        probe_eval     = understanding.get("probe_evaluation", {}) or {}
        acknowledgment = probe_eval.get("acknowledgment") or ""

        # Learner used this beat to ask something new rather than answer the
        # check — pivot to answer it like any other follow-on. They land
        # back in this same confirmation loop once that new thread wraps up.
        raw_follow_on = understanding.get("follow_on_question")
        if raw_follow_on and not _is_blank(str(raw_follow_on)):
            result = await answer_learner_question(
                question=raw_follow_on,
                active_section=active_section,
                lesson=lesson,
                resume_pointer=resume_pointer,
                conversation_history=conv_history,
                examples_given=examples_given,
                board_state=board_state,
                model=model,
            )
            current_core_explanation = result.get("core_explanation") or current_core_explanation
            payload = result["envelope"]
            if acknowledgment:
                payload = _wrap_answer_envelope(
                    question=raw_follow_on, resume_pointer=resume_pointer,
                    steps=result["steps"], section_type="ANSWER_EXPLANATION",
                    title=payload["sections"][0]["title"],
                    purpose=payload["sections"][0]["purpose"],
                    leading_speak=acknowledgment,
                )
            return {
                "action":                      "ANSWER",
                "payload":                     payload,
                "examples_given":              examples_given + 1,
                "understanding_status":        UnderstandingStatus.PENDING,
                "approaches_used":             used_approaches,
                "probe_question":              result["probe_question"],
                "timeout_grace_used":          timeout_grace_used,
                "resume_lesson":               False,
                "awaiting_final_confirmation": False,
                "board_state":                 result.get("board_state", board_state or []),
                "core_explanation":            current_core_explanation,
            }

        status = understanding.get("status", UnderstandingStatus.UNCERTAIN)

        if status == UnderstandingStatus.CONFIRMED:
            # Genuinely confirmed now, not just a lucky probe answer — safe
            # to actually resume the lesson.
            if acknowledgment:
                ack_envelope = _wrap_answer_envelope(
                    question=question,
                    resume_pointer=resume_pointer,
                    steps=[{
                        "id": "final_ack_step",
                        "objective": "Warmly close out before resuming the lesson",
                        "events": [_make_speak_event(acknowledgment)],
                    }],
                    section_type="ANSWER_ACKNOWLEDGMENT",
                    title="Great — moving on",
                    purpose="Speak the closing confirmation before resuming the lesson.",
                )
                return {
                    "action":                      "ANSWER",
                    "payload":                     ack_envelope,
                    "examples_given":              examples_given,
                    "understanding_status":        UnderstandingStatus.CONFIRMED,
                    "approaches_used":             used_approaches,
                    "probe_question":              None,
                    "timeout_grace_used":          timeout_grace_used,
                    "resume_lesson":               True,
                    "awaiting_final_confirmation": False,
                    "board_state":                 board_state or [],
                    "core_explanation":            current_core_explanation,
                }
            return {
                "action": "RESUME",
                "payload": {
                    "message":              "Learner confirmed real understanding. Resuming the lesson.",
                    "reason":               "confirmed",
                    "understanding_result": understanding,
                    "resume":               resume_pointer,
                },
                "examples_given":              examples_given,
                "understanding_status":        UnderstandingStatus.CONFIRMED,
                "approaches_used":             used_approaches,
                "probe_question":              None,
                "timeout_grace_used":          timeout_grace_used,
                "resume_lesson":               True,
                "awaiting_final_confirmation": False,
                "board_state":                 board_state or [],
                "core_explanation":            current_core_explanation,
            }

        # Still shaky — they nailed the probe but aren't actually confident
        # ("kind of?", "not really", another attempt at the concept). Give
        # one more explanation instead of forcing them back into the lesson
        # on a false-positive confirmation.
        current_approach = previous_approach or APPROACH_PROGRESSION[0]
        result = await escalate_with_example(
            question=question,
            active_section=active_section,
            lesson=lesson,
            resume_pointer=resume_pointer,
            conversation_history=conv_history,
            example_number=examples_given,
            previous_approach=current_approach,
            probe_question=probe_question,
            board_state=board_state,
            model=model,
        )
        current_core_explanation = result.get("core_explanation") or current_core_explanation
        payload = result["envelope"]
        if acknowledgment:
            payload = _wrap_answer_envelope(
                question=question, resume_pointer=resume_pointer,
                steps=result["steps"], section_type="ANSWER_ESCALATION",
                title=payload["sections"][0]["title"],
                purpose=payload["sections"][0]["purpose"],
                leading_speak=acknowledgment,
            )
        return {
            "action":                      "ESCALATE",
            "payload":                     payload,
            "examples_given":              result["examples_given"],
            "understanding_status":        UnderstandingStatus.PENDING,
            "approaches_used":             used_approaches + [result["approach_used"]],
            "probe_question":              result["probe_question"],
            "timeout_grace_used":          timeout_grace_used,
            "resume_lesson":               False,
            "awaiting_final_confirmation": False,
            "board_state":                 result.get("board_state", board_state or []),
            "core_explanation":            current_core_explanation,
        }

    # ── MICRO EXPLANATION: learner replied to a confusion probe ──────────────
    if confusion_location is not None:
        understanding = await classify_understanding(
            learner_response=confusion_location,
            question=question,
            examples_given=examples_given,
            probe_question=probe_question,
            conversation_history=conv_history,
            model=model,
        )

        # If they understand, don't jump straight back into the lesson on
        # one correctly-graded probe. Acknowledge it, then hand off to the
        # soft "does that make sense" check — the lesson only resumes once
        # THAT comes back confirmed (see the awaiting_final_confirmation
        # branch below).
        #
        # IMPORTANT: gate this on the actual probe grading
        # (was_answer_attempt + correctness == CORRECT), NOT on whether
        # `acknowledgment` happens to be non-empty. The classifier doesn't
        # reliably leave acknowledgment blank for plain "yes I get it"
        # replies (despite being told to) — gating on acknowledgment alone
        # means a learner confirming the SOFT CHECK itself ("yeah that
        # makes sense") can get misread as a fresh correct probe answer,
        # spinning up another confirmation check forever instead of
        # resuming.
        if understanding.get("status") == UnderstandingStatus.CONFIRMED:
            probe_eval_local = understanding.get("probe_evaluation", {}) or {}
            probe_ack = probe_eval_local.get("acknowledgment") or ""
            was_probe_confirmed = (
                bool(probe_eval_local.get("was_answer_attempt"))
                and probe_eval_local.get("correctness") == ProbeOutcome.CORRECT
            )
            if was_probe_confirmed:
                return await _build_confirmation_check_result(
                    question=question,
                    active_section=active_section,
                    lesson=lesson,
                    resume_pointer=resume_pointer,
                    acknowledgment=probe_ack,
                    examples_given=examples_given,
                    used_approaches=used_approaches,
                    timeout_grace_used=timeout_grace_used,
                    board_state=board_state,
                    core_explanation=current_core_explanation,
                    model=model,
                )

            # Genuine confirmation-in-their-own-words (not a graded probe
            # attempt) — speak the acknowledgment if there is one, then
            # resume for real. No second check needed.
            if probe_ack:
                ack_envelope = _wrap_answer_envelope(
                    question=question,
                    resume_pointer=resume_pointer,
                    steps=[{
                        "id": "ack_step",
                        "objective": "Acknowledge the learner's confirmation",
                        "events": [_make_speak_event(probe_ack)],
                    }],
                    section_type="ANSWER_ACKNOWLEDGMENT",
                    title="Acknowledging your answer",
                    purpose="Speak the confirmation before resuming the lesson.",
                )
                return {
                    "action":                      "ANSWER",
                    "payload":                     ack_envelope,
                    "examples_given":              examples_given,
                    "understanding_status":        UnderstandingStatus.CONFIRMED,
                    "approaches_used":             used_approaches,
                    "probe_question":              None,
                    "timeout_grace_used":          timeout_grace_used,
                    "resume_lesson":               True,
                    "awaiting_final_confirmation": False,
                    "board_state":                 board_state or [],
                    "core_explanation":            current_core_explanation,
                }

            # No spoken acknowledgment — plain silent resume
            return {
                "action": "RESUME",
                "payload": {
                    "message": "Learner has confirmed understanding during probe.",
                    "reason": "confirmed",
                    "understanding_result": understanding,
                    "resume": resume_pointer,
                },
                "examples_given":              examples_given,
                "understanding_status":        UnderstandingStatus.CONFIRMED,
                "approaches_used":             used_approaches,
                "probe_question":              None,
                "timeout_grace_used":          timeout_grace_used,
                "resume_lesson":               True,
                "awaiting_final_confirmation": False,
                "board_state":                 board_state or [],
                "core_explanation":            current_core_explanation,
            }

        result = await generate_micro_explanation(
            confusion_location=confusion_location,
            question=question,
            active_section=active_section,
            lesson=lesson,
            resume_pointer=resume_pointer,
            board_state=board_state,
            model=model,
        )
        current_core_explanation = result.get("core_explanation") or current_core_explanation
        return {
            "action":                      "MICRO",
            "payload":                     result["envelope"],
            "examples_given":              examples_given,
            "understanding_status":        UnderstandingStatus.PENDING,
            "approaches_used":             used_approaches,
            "probe_question":              result["probe_question"],
            "timeout_grace_used":          timeout_grace_used,
            "resume_lesson":               False,
            "awaiting_final_confirmation": False,
            "board_state":                 result.get("board_state", board_state or []),
            "core_explanation":            current_core_explanation,
        }

    # ── TURN 1: Initial answer ───────────────────────────────────────────────
    if learner_response is None:
        bank_match = None
        if bank:
            sec_id = str(active_section.get("id", active_section.get("type", "unknown")))
            bank_match = search_question_bank(question, bank, sec_id, active_section)

        result = await answer_learner_question(
            question=question,
            active_section=active_section,
            lesson=lesson,
            resume_pointer=resume_pointer,
            conversation_history=conv_history,
            examples_given=0,
            bank_match=bank_match,
            board_state=board_state,
            model=model,
        )
        current_core_explanation = result.get("core_explanation") or current_core_explanation
        return {
            "action":                      "ANSWER",
            "payload":                     result["envelope"],
            "examples_given":              1,
            "understanding_status":        UnderstandingStatus.PENDING,
            "approaches_used":             [result["approach_used"]],
            "probe_question":              result["probe_question"],
            "timeout_grace_used":          False,
            "resume_lesson":               False,
            "awaiting_final_confirmation": False,
            "board_state":                 result.get("board_state", board_state or []),
            "core_explanation":            current_core_explanation,
        }

    # ── TIMEOUT CHECK: learner is silent and the clock has run out ──────────
    # A real (non-blank) reply always wins over the timer, so this only
    # triggers when learner_response is blank/empty AND enough wall-clock
    # time has actually passed since the last probe.
    if (
        _is_blank(learner_response)
        and seconds_since_prompt is not None
        and seconds_since_prompt >= timeout_seconds
    ):
        if examples_given >= MAX_EXAMPLES_BEFORE_PROBE or timeout_grace_used:
            # Either we've already tried enough angles, or we already gave
            # one grace example and the learner is STILL silent — resume.
            return {
                "action": "RESUME",
                "payload": {
                    "message": "Learner did not respond within the time window. Resuming the lesson.",
                    "reason":  "timeout",
                    "resume":  resume_pointer,
                },
                "examples_given":              examples_given,
                "understanding_status":        UnderstandingStatus.CONFIRMED,
                "approaches_used":             used_approaches,
                "probe_question":              None,
                "timeout_grace_used":          timeout_grace_used,
                "resume_lesson":               True,
                "awaiting_final_confirmation": False,
                "board_state":                 board_state or [],
                "core_explanation":            current_core_explanation,
            }

        # Haven't hit the example ceiling yet — give exactly one more
        # ("grace") example, then re-ask. This re-arms the caller's clock
        # because a brand new probe is being issued.
        current_approach = previous_approach or APPROACH_PROGRESSION[0]
        result = await escalate_with_example(
            question=question,
            active_section=active_section,
            lesson=lesson,
            resume_pointer=resume_pointer,
            conversation_history=conv_history,
            example_number=examples_given,
            previous_approach=current_approach,
            probe_question=probe_question,
            board_state=board_state,
            model=model,
        )
        current_core_explanation = result.get("core_explanation") or current_core_explanation
        return {
            "action":                      "ESCALATE",
            "payload":                     result["envelope"],
            "examples_given":              result["examples_given"],
            "understanding_status":        UnderstandingStatus.PENDING,
            "approaches_used":             used_approaches + [result["approach_used"]],
            "probe_question":              result["probe_question"],
            "timeout_grace_used":          True,
            "resume_lesson":               False,
            "awaiting_final_confirmation": False,
            "board_state":                 result.get("board_state", board_state or []),
            "core_explanation":            current_core_explanation,
        }

    # ── TURN 2+: Classify the learner's reply via the agent ──────────────────
    understanding = await classify_understanding(
        learner_response=learner_response,
        question=question,
        examples_given=examples_given,
        probe_question=probe_question,
        conversation_history=conv_history,
        model=model,
    )
    probe_eval    = understanding.get("probe_evaluation", {}) or {}
    acknowledgment = probe_eval.get("acknowledgment") or ""

    # Follow-on question detected? Treat it as a brand-new question, not a
    # confirmation/probe-answer at all. Note: the learner may have ALSO
    # correctly/partially answered the probe in the same reply ("5, but
    # what if it's negative?") — if classify_understanding produced an
    # acknowledgment for that, speak it first so the correct answer doesn't
    # go silently unconfirmed right before we pivot to the new question.
    raw_follow_on = understanding.get("follow_on_question")
    if raw_follow_on and not _is_blank(str(raw_follow_on)):
        result = await answer_learner_question(
            question=raw_follow_on,
            active_section=active_section,
            lesson=lesson,
            resume_pointer=resume_pointer,
            conversation_history=conv_history,
            examples_given=examples_given,
            board_state=board_state,
            model=model,
        )
        current_core_explanation = result.get("core_explanation") or current_core_explanation
        payload = result["envelope"]
        if acknowledgment:
            payload = _wrap_answer_envelope(
                question=raw_follow_on, resume_pointer=resume_pointer,
                steps=result["steps"], section_type="ANSWER_EXPLANATION",
                title=payload["sections"][0]["title"],
                purpose=payload["sections"][0]["purpose"],
                leading_speak=acknowledgment,
            )
        return {
            "action":                      "ANSWER",
            "payload":                     payload,
            "examples_given":              examples_given + 1,
            "understanding_status":        UnderstandingStatus.PENDING,
            "approaches_used":             used_approaches + [result["approach_used"]],
            "probe_question":              result["probe_question"],
            "timeout_grace_used":          timeout_grace_used,
            "resume_lesson":               False,
            "awaiting_final_confirmation": False,
            "board_state":                 result.get("board_state", board_state or []),
            "core_explanation":            current_core_explanation,
        }

    status = understanding.get("status", UnderstandingStatus.UNCERTAIN)

    # ── CONFIRMED: learner understood (or nailed the probe) ─────────────────
    # Two different things both land here, and they are NOT treated the same:
    #
    #   1. The learner directly answered the AWAIT_RESPONSE probe and got it
    #      right (probe_evaluation.was_answer_attempt is True AND
    #      correctness == CORRECT). One correct answer is not proof the
    #      concept landed, so this does NOT resume yet — it hands off to
    #      the soft "does that make sense" confirmation check. The lesson
    #      only resumes once THAT check itself comes back confirmed (see
    #      the awaiting_final_confirmation branch above).
    #
    #   2. The learner said, in their own words, that they understand
    #      ("okay", "got it", "makes sense") with no specific probe answer
    #      to grade. That IS their confirmation — no second check needed —
    #      so this falls through to a plain RESUME (with the acknowledgment
    #      spoken first if the classifier gave one).
    #
    # NOTE: gate on `was_answer_attempt` + `correctness == CORRECT`, NOT on
    # whether `acknowledgment` is merely non-empty. The classifier doesn't
    # reliably leave acknowledgment blank for a plain "yes I get it" reply
    # (despite being told to) — gating on acknowledgment alone means a
    # learner confirming the SOFT CHECK itself gets misread as having just
    # answered a fresh probe correctly, which spins up another confirmation
    # check forever instead of ever resuming.
    was_probe_confirmed = (
        bool(probe_eval.get("was_answer_attempt"))
        and probe_eval.get("correctness") == ProbeOutcome.CORRECT
    )
    if status == UnderstandingStatus.CONFIRMED:
        if was_probe_confirmed:
            return await _build_confirmation_check_result(
                question=question,
                active_section=active_section,
                lesson=lesson,
                resume_pointer=resume_pointer,
                acknowledgment=acknowledgment,
                examples_given=examples_given,
                used_approaches=used_approaches,
                timeout_grace_used=timeout_grace_used,
                board_state=board_state,
                core_explanation=current_core_explanation,
                model=model,
            )

        # Genuine confirmation-in-their-own-words — speak the acknowledgment
        # if there is one, then resume for real. No second check needed.
        if acknowledgment:
            ack_envelope = _wrap_answer_envelope(
                question=question,
                resume_pointer=resume_pointer,
                steps=[{
                    "id": "ack_step",
                    "objective": "Acknowledge the learner's confirmation",
                    "events": [_make_speak_event(acknowledgment)],
                }],
                section_type="ANSWER_ACKNOWLEDGMENT",
                title="Acknowledging your answer",
                purpose="Speak the confirmation before resuming the lesson.",
            )
            return {
                "action":                      "ANSWER",
                "payload":                     ack_envelope,
                "examples_given":              examples_given,
                "understanding_status":        UnderstandingStatus.CONFIRMED,
                "approaches_used":             used_approaches,
                "probe_question":              None,
                "timeout_grace_used":          timeout_grace_used,
                "resume_lesson":               True,
                "awaiting_final_confirmation": False,
                "board_state":                 board_state or [],
                "core_explanation":            current_core_explanation,
            }

        # No spoken acknowledgment — plain silent resume
        return {
            "action": "RESUME",
            "payload": {
                "message":              "Learner has confirmed understanding. Resuming the lesson.",
                "reason":               "confirmed",
                "understanding_result": understanding,
                "resume":               resume_pointer,
            },
            "examples_given":              examples_given,
            "understanding_status":        UnderstandingStatus.CONFIRMED,
            "approaches_used":             used_approaches,
            "probe_question":              None,
            "timeout_grace_used":          timeout_grace_used,
            "resume_lesson":               True,
            "awaiting_final_confirmation": False,
            "board_state":                 board_state or [],
            "core_explanation":            current_core_explanation,
        }

    # ── ESCALATED / MAX EXAMPLES: probe instead of yet another example ───────
    if (
        status == UnderstandingStatus.ESCALATED
        or examples_given >= MAX_EXAMPLES_BEFORE_PROBE
    ):
        result = await probe_confusion_point(
            question=question,
            active_section=active_section,
            lesson=lesson,
            resume_pointer=resume_pointer,
            examples_given=examples_given,
            model=model,
        )
        payload = result["envelope"]
        if acknowledgment:
            payload = _wrap_answer_envelope(
                question=question, resume_pointer=resume_pointer,
                steps=result["steps"], section_type="ANSWER_PROBE",
                title=payload["sections"][0]["title"],
                purpose=payload["sections"][0]["purpose"],
                leading_speak=acknowledgment,
            )
        return {
            "action":                      "PROBE",
            "payload":                     payload,
            "examples_given":              examples_given,
            "understanding_status":        UnderstandingStatus.ESCALATED,
            "approaches_used":             used_approaches,
            "probe_question":              result["probe_question"],
            "timeout_grace_used":          timeout_grace_used,
            "resume_lesson":               False,
            "awaiting_final_confirmation": False,
            "board_state":                 board_state or [],
            "core_explanation":            current_core_explanation,
        }

    # ── NOT CONFIRMED / UNCERTAIN: escalate with a new approach ─────────────
    # If the learner attempted (and missed) the probe, hand the specific
    # wrong answer to escalate_with_example() so it responds to THAT mistake
    # instead of giving a generic re-explanation.
    wrong_answer_note = None
    if probe_eval.get("was_answer_attempt") and probe_eval.get("correctness") == ProbeOutcome.INCORRECT:
        wrong_answer_note = learner_response

    current_approach = previous_approach or APPROACH_PROGRESSION[0]
    result = await escalate_with_example(
        question=question,
        active_section=active_section,
        lesson=lesson,
        resume_pointer=resume_pointer,
        conversation_history=conv_history,
        example_number=examples_given,
        previous_approach=current_approach,
        wrong_answer_note=wrong_answer_note,
        probe_question=probe_question,
        board_state=board_state,
        model=model,
    )
    current_core_explanation = result.get("core_explanation") or current_core_explanation
    payload = result["envelope"]
    # When wrong_answer_note was set, escalate_with_example() was already told
    # ("Open by acknowledging this specific attempt — name what they said") to
    # open with its own acknowledgment of this exact wrong answer. Prepending
    # the grader's acknowledgment on top of that double-acknowledges the
    # same miss back-to-back (e.g. "Close, but not quite..." immediately
    # followed by "Ah, close! You said..."). Only inject leading_speak when
    # escalate_with_example had nothing of its own to acknowledge.
    if acknowledgment and not wrong_answer_note:
        payload = _wrap_answer_envelope(
            question=question, resume_pointer=resume_pointer,
            steps=result["steps"], section_type="ANSWER_ESCALATION",
            title=payload["sections"][0]["title"],
            purpose=payload["sections"][0]["purpose"],
            leading_speak=acknowledgment,
        )

    return {
        "action":                      "ESCALATE",
        "payload":                     payload,
        "examples_given":              result["examples_given"],
        "understanding_status":        UnderstandingStatus.PENDING,
        "approaches_used":             used_approaches + [result["approach_used"]],
        "probe_question":              result["probe_question"],
        "timeout_grace_used":          timeout_grace_used,
        "resume_lesson":               False,
        "awaiting_final_confirmation": False,
        "board_state":                 result.get("board_state", board_state or []),
        "core_explanation":            current_core_explanation,
    }