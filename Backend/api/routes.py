"""
Lumina Course Creation + Lesson Planning API
═══════════════════════════════════════════════════════════════════════════════
COURSE CREATION ENDPOINTS

  POST /create/course/extract-pdf
    Accepts a PDF upload. Runs the full extraction pipeline from extracting_engine.py:
      PyMuPDF → text chunks → LLM lesson generator → structured course plan.
    Returns extraction_meta (pre-fills topic/subject in Step 1), source_summary
    (store this — it grounds all subsequent calls), and a preliminary_plan.

  POST /create/course/prerequisites
    Step 1 → Step 2 transition.
    Given topic + goal (and optionally source_summary from a PDF upload),
    returns 3–4 AI-identified prerequisite strength fields for Step 2.
    PDF path: fields are grounded in the actual subject matter of the PDF.
    AI path:  fields are inferred generically from topic + goal.

  POST /create/course
    Step 2 → Step 3 transition.
    Generates the fully personalised course with per-lesson prerequisite
    revision. Both paths converge here and return the same response schema
    so the frontend renders Step 3 identically for both.

LESSON PLANNING ENDPOINTS (lesson_engine.py)

  POST /lesson/generate
    Turns a single lesson stub from the course plan into a fully planned,
    board-ready lesson — the four-level hierarchy that streaming_engine.py
    executes directly: Lesson → Sections → Steps → Presentation Events
    (SPEAK, WRITE, HIGHLIGHT, UNDERLINE, CIRCLE, ANNOTATE, ERASE, REVEAL,
    PAUSE, AWAIT_RESPONSE), each event flagged sync_with_previous for
    concurrent delivery (e.g. writing on the board while still talking).

    STEM-first rule enforced: every CONCEPT_INTRODUCTION section is
    immediately followed by 2–3 WORKED_EXAMPLE sections and a practice
    section (GUIDED_PRACTICE / INDEPENDENT_PRACTICE).

    This output is passed unchanged as `teaching_script` to
    POST /stream/session/create — streaming_engine.py interprets it as the
    lesson_engine format directly (the field name is kept only for backward
    compatibility; see streaming_engine.py's module docstring).

STREAMING ENDPOINTS (streaming_engine.py, lesson_engine format)

  POST /stream/session/create
    Creates a new streaming session from a lesson_engine lesson dict (and
    optional pre-warmed question bank). Returns a session_id for all
    subsequent calls.

  GET  /stream/session/state?session_id=...
    Returns a serializable snapshot of the session's current state
    (current_section_index, current_step_index, total_sections, ...).

  GET  /stream/lesson?session_id=...               [SSE]
    Primary SSE stream. Delivers the lesson from the current position,
    emitting typed events: SECTION_START/STEP_START structure events,
    TEACHER_SAYS narration, BOARD_WRITE_START/APPEND/COMPLETE (or BOARD_WRITE
    in non-sync mode), board annotation events (BOARD_HIGHLIGHT/UNDERLINE/
    CIRCLE/ANNOTATE/ERASE/REVEAL), STEP_PAUSE, and LEARNER_CHECKPOINT.
    Concurrent events (sync_with_previous: true) arrive interleaved — e.g.
    board characters and speech words mixed together. Ends with LESSON_PAUSE
    (if interrupted) or LESSON_COMPLETE (if finished).

  POST /stream/pause
    Sets the session's pause flag. The active stream detects the flag at
    the next natural break and emits LESSON_PAUSE before closing. The
    frontend then opens POST /answer/ask.

  POST /stream/hand-raise
    Signals a soft "raised hand" — does NOT cut delivery mid-word like
    /stream/pause. Acknowledged in-stream (HAND_RAISE_ACK) at the next
    group boundary, then promoted into a real LESSON_PAUSE (raised_as_hand:
    true) once the current step finishes cleanly. Mirrors a real classroom:
    the teacher finishes her thought, then turns to the learner.

  POST /stream/hand-lower
    Cancels a previously raised hand before it's promoted into a pause.
    No-op (but safe) if never raised or already promoted.

  GET  /stream/resume?session_id=...               [SSE]
    Opens a new SSE stream after a confirmed Q&A (or a completed practice
    attempt). Generates an LLM-produced bridge phrase (never a template,
    wrapped in RESUME_BRIDGE begin/end events) then delegates back into the
    GET /stream/lesson event stream from the stored position.

  GET  /stream/sessions                            [admin]
    Lists all in-memory sessions (lightweight summary).

  DELETE /stream/session/{session_id}              [admin]
    Evicts a single session from memory.

  POST /stream/sessions/evict-stale               [admin]
    Removes sessions idle longer than max_age_seconds (default 7200).

ANSWER ENGINE ENDPOINTS (answer_engine.py)

  POST /answer/anticipate
    Pre-scans an entire teaching script and returns a question bank. Available
    as a standalone utility, but the primary flow no longer requires calling
    this before starting the lesson — /stream/session/create now fires
    launch_background_anticipation() automatically (no blocking wait).

  POST /answer/ask                                 ← primary Q&A endpoint
    Manages the full Q&A lifecycle: initial answer, understanding check,
    escalation to a new teaching approach, and confusion probing. The
    frontend calls this on every turn, forwarding state from prior responses.
    Turn 2+ must include probe_question, seconds_since_prompt, and
    timeout_grace_used (all returned in the prior response) so the engine
    can grade direct probe answers and honour the silence-timeout policy.

  POST /answer/understand
    Classifies a learner reply as CONFIRMED / UNCERTAIN / NOT_CONFIRMED.
    Lightweight standalone call — also invoked internally by /answer/ask.

  POST /answer/escalate
    Generates a re-explanation using a completely different teaching approach
    (ALGEBRAIC → ANALOGY → NUMERICAL → CONTRAST → BACKWARDS → STORY → VISUAL).
    Returns an action envelope with an event-stream payload identical in shape
    to a lesson section (SPEAK / WRITE / AWAIT_RESPONSE events).

  POST /answer/probe
    After MAX_EXAMPLES, generates a targeted probe to locate the learner's
    exact confusion point, then produces a micro-explanation that addresses it.
    Both turns return event-stream envelopes — same shape as lesson sections.

═══════════════════════════════════════════════════════════════════════════════
FULL FLOW

  Course creation — AI path (no_source=True):
    Step 1  → POST /create/course/prerequisites  { topic, goal }
    Step 2  → (user rates prerequisites)
    Step 3  → POST /create/course               { topic, goal, prerequisites }

  Course creation — PDF path (no_source=False):
    Step 1  → POST /create/course/extract-pdf   { file }
                ↳ frontend stores source_summary + extraction_meta.inferred_title
              → POST /create/course/prerequisites { topic, goal, source_summary }
    Step 2  → (user rates prerequisites)
    Step 3  → POST /create/course               { topic, goal, prerequisites,
                                                  no_source=False, source_summary }

  Lesson playback — full pipeline:
    User clicks a lesson in Lesson.jsx( Lesson page with whiteboard lessons )
              → POST /lesson/generate            { lesson stub + prerequisites }
              → POST /stream/session/create      { teaching_script }
                 ↳ returns session_id
                 ↳ fires launch_background_anticipation(lesson) — no waiting
              → GET  /stream/lesson?session_id=… [SSE — lesson begins immediately,
                 question bank builds in the background]

  Mid-lesson Q&A:
    Learner types a question
              → POST /stream/pause               { session_id, question }
              → POST /answer/ask                 { question, active_segment, … }
                 ↳ turns 2+: include examples_given, approaches_used, learner_response
                 ↳ if NOT_CONFIRMED: POST /answer/escalate
                 ↳ after MAX_EXAMPLES: POST /answer/probe
              → (when understanding_status == CONFIRMED)
              → GET  /stream/resume?session_id=… [SSE — bridge + continuation]
═══════════════════════════════════════════════════════════════════════════════
"""
import asyncio
import json
import logging

from typing import Dict, Optional, List

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from prompts.create_course_prompts import CreateCoursePrompt
from services.assert_client import _assert_client

from pipelines import llm_gateway as gateway

from utils.prereq_helpers import _format_prereq_block
from utils.answer_engine_helpers import (
    _flatten_escalation,
    _flatten_micro,
    _flatten_probe
)
from schemas.create_course import (
    PrerequisiteRequest, 
    CourseRequest,
    RATING_LABELS
)
from schemas.lesson_plan import LessonGenerateRequest
from schemas.streaming import (
    CreateSessionRequest,
    PauseLessonRequest,
    HandRaiseRequest,
    HandLowerRequest,
    EvictStaleRequest
)
from schemas.answer_engine import (
    AnticipateRequest,
    AnswerSessionRequest,
    ClassifyUnderstandingRequest,
    EscalateRequest,
    ProbeRequest
)

from pipelines.extracting_engine import run_extraction_pipeline, MAX_PDF_BYTES
from pipelines.lesson_engine import generate_lesson
from pipelines.streaming_engine import (
    create_session,
    stream_lesson,
    pause_lesson,
    raise_hand,
    lower_hand,
    resume_lesson,
    get_session_state,
    list_sessions,
    evict_session,
    evict_stale_sessions,
    store_answer_envelope,
    stream_answer_envelope

)
from pipelines.answer_engine import (
    anticipate_questions,
    launch_background_anticipation,
    handle_answer_session,
    classify_understanding,
    escalate_with_example,
    probe_confusion_point,
    generate_micro_explanation
)

logger = logging.getLogger(__name__)
router = APIRouter()



# Per-session background anticipation tasks.
# Keyed by session_id. Fired immediately in /stream/session/create so the
# lesson starts streaming with zero wait. /answer/ask looks up the task and
# passes it straight into handle_answer_session(), which calls
# _resolve_question_bank() — that checks task.done() without ever blocking.
# Entries are pruned when sessions are evicted (see evict_* routes below).
_bg_anticipation_tasks: Dict[str, "asyncio.Task"] = {}

# ─── Active-section resolution ────────────────────────────────────────────────
# active_segment in every /answer/* request body is populated CLIENT-SIDE from
# the frontend's locally-tracked "current section" pointer. 
def _resolve_active_section(
    payload_active_segment: Dict,
    teaching_script: Dict,
    session_id: Optional[str],
) -> Dict:
    """
    Return the section that should be treated as "active" for this Q&A turn.

    Prefers get_session_state(session_id)['pause_context']['segment_index']
    (the server's own record of what it actually paused on) over the
    client-supplied active_segment whenever a session_id is present and that
    lookup resolves cleanly. Falls back to the client-supplied active_segment
    for standalone calls with no session_id, sessions with no pause_context
    yet, or an out-of-range segment_index.

    Also trims the resolved section's steps down to pause_context['step_index']
    (exclusive) when present, so the returned section only contains steps that
    finished delivering before the pause — not the full planned section, and
    not the step that was in progress (or not yet started) when the pause
    landed. Without this, answer_engine.py's section-context prompt can treat
    steps that were never fully shown to the learner as already on the board.
    The client-supplied fallback path returns whatever the client sent,
    untrimmed.
    """
    if not session_id:
        return payload_active_segment

    try:
        state = get_session_state(session_id)
    except (KeyError, ValueError):
        return payload_active_segment

    pause_context = state.get("pause_context")
    if not pause_context:
        return payload_active_segment

    segment_index = pause_context.get("segment_index")
    sections = teaching_script.get("sections", [])
    if segment_index is None or not (0 <= segment_index < len(sections)):
        return payload_active_segment

    authoritative_section = sections[segment_index]

    # Trim to only the steps that finished delivering before the pause.
    # step_index itself is NOT safe to include: _deliver_section sets
    # current_step_index = step_idx both when a step is only partially
    # delivered (pause/hand-raise interrupt at a group boundary mid-step,
    # not a step boundary — see _deliver_step/_promote_hand_raise) and
    # when the step hasn't started at all yet (pause detected in the gap
    # between steps). Only steps strictly before step_index are guaranteed
    # fully on the board, so the slice must be exclusive.
    step_index = pause_context.get("step_index")
    if step_index is not None:
        authoritative_section = dict(authoritative_section)
        authoritative_section["steps"] = authoritative_section.get("steps", [])[:step_index]

    client_id = payload_active_segment.get("id") or payload_active_segment.get("type")
    server_id = authoritative_section.get("id") or authoritative_section.get("type")
    if client_id != server_id:
        print(
            f"answer_ask: active_segment mismatch for session {session_id} — "
            f"client sent {client_id!r}, session pause_context says "
            f"{server_id!r} (segment_index={segment_index}). Using the "
            "session's version."
        )

    return authoritative_section



async def _sse_stream(generator):
    """
    Wrap an AsyncGenerator[Dict, None] as an SSE byte stream.
    Each dict is JSON-encoded as:  data: {...}\\n\\n
    Any exception mid-stream yields a terminal ERROR event.
    """
    try:
        async for event in generator:
            yield f"data: {json.dumps(event)}\n\n"
    except Exception as exc:
        print("SSE ERROR: ",exc)
        yield f"data: {json.dumps({'event': 'ERROR', 'detail': str(exc)})}\n\n"


_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection":    "keep-alive",
    "X-Accel-Buffering": "no",   # prevent nginx from buffering SSE
}



# ════════════════════════════════════════════════════════════════════════════
# HEALTH
# ════════════════════════════════════════════════════════════════════════════
@router.get("/health")
async def health():
    """
    Liveness probe.
    Lesson.jsx polls this on mount (2 s timeout) to decide whether to use
    backend SSE streaming or fall back to local KaTeX-only rendering.

    Response: { "status": "ok", "ai": <bool> }
    """
    return {"status": "ok", "ai": gateway.is_ready()}


# ════════════════════════════════════════════════════════════════════════════
# COURSE CREATION ROUTES
# ════════════════════════════════════════════════════════════════════════════

@router.post("/create/course/extract-pdf")
async def extract_pdf_course(
    file:  UploadFile = File(...),
    model: Optional[str] = Form(None),
):
    """
    Step 1 — PDF path only.
    Accepts a PDF upload and runs the full Lumina extraction pipeline:
      Stage 1 — PyMuPDF span extraction with font metadata
      Stage 2 — Heading detection → section segmentation → key-term extraction
      Stage 3 — LLM Lesson Generator: text chunks → rich lesson objects
      Stage 4 — Structured output dict

    Frontend usage:
      1. Call this when the user uploads a PDF in Step 1.
      2. Store source_summary in React state (it flows into /prerequisites
         and /create/course so both are grounded in the PDF content).
      3. Use extraction_meta.inferred_title to pre-fill the topic input.

    Response shape:
    {
      "extraction_meta": {
          "inferred_title":   str,
          "inferred_subject": str,
          "inferred_grade":   str,
          "total_pages":      int,
          "sections_count":   int,
      },
      "source_summary":   str,    ← STORE AND FORWARD to subsequent routes
      "preliminary_plan": { ... },
      "key_concepts":     [...],
    }
    """
    _assert_client()
    content_type = file.content_type or ""
    allowed_types = {
        "application/pdf",
        "application/octet-stream",
        "binary/octet-stream",
    }
    if content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Only PDF files are accepted. "
                f"Received content type: '{content_type or 'none'}'. "
                f"If you are uploading a valid PDF, try renaming the file to end in .pdf."
            ),
        )

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(file_bytes) > MAX_PDF_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"PDF exceeds the {MAX_PDF_BYTES // (1024 * 1024)} MB limit.",
        )

    try:
        result = await run_extraction_pipeline(file_bytes, model)
    except ValueError as exc:
        # Image-only PDF or no extractable text
        raise HTTPException(status_code=422, detail=str(exc))
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Lesson generator returned malformed JSON. Please retry.",
        )
    except Exception as exc:
        print(f"extract_pdd_course Error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    return result


@router.post("/create/course/prerequisites")
async def get_course_prerequisites(payload: PrerequisiteRequest):
    """
    Step 1 → Step 2 transition.

    Returns 3–4 prerequisite strength fields for the student to self-rate.

    AI path  (source_summary absent) — fields inferred from topic + goal.
    PDF path (source_summary present) — fields grounded in the actual content
    structure of the uploaded PDF (e.g. specific theorems, techniques, or
    formulas mentioned in the source will surface as prerequisites).

    Response: JSON array of { id, label } objects — the same shape the
    frontend uses to render Step 2 rating buttons.
    """
    print(f"PREREQ MODEL: {payload.model}")
    if not payload.topic.strip():
        raise HTTPException(status_code=400, detail="Course topic is required.")
    if not payload.goal.strip():
        raise HTTPException(status_code=400, detail="Learning goal is required.")
    _assert_client()

    user_content = (
        f"Topic        : {payload.topic}\n"
        f"Learning Goal: {payload.goal}"
    )
    if payload.source_summary:
        user_content += (
            f"\n\nSOURCE MATERIAL (derive subject-specific prerequisites from this):\n"
            f"{payload.source_summary[:1600]}"
        )
    user_content += "\n\nIdentify the prerequisite baseline fields now."

    try:
        result = await gateway.complete_json(
            user_content,
            model=payload.model,
            system=CreateCoursePrompt.CREATE_PREREQ_SYSTEM,
            response_format="text",
            max_tokens=400,
            temperature=0.3,
        )
        # OpenAI's json_object response mode forbids a bare top-level array,
        # so providers that enforce it (OpenAI) will wrap requested array
        # as {"prerequisites": [...]} (or similar) even though the system
        # prompt asks for a plain array and this route's contract promises
        # one. Unwrap defensively so the frontend always gets what it expects
        # regardless of which provider/model answered the call.
        if isinstance(result, dict):
            if isinstance(result.get("prerequisites"), list):
                result = result["prerequisites"]
            else:
                list_values = [v for v in result.values() if isinstance(v, list)]
                if len(list_values) == 1:
                    result = list_values[0]
        print(result)
        return result
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Failed to parse prerequisite fields. Please retry.",
        )
    except Exception as exc:
        print(f"get_course_prerequisite Error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/create/course")
async def create_course(payload: CourseRequest):
    """
    Step 2 → Step 3 transition.

    Takes the topic, goal, and rated prerequisites and returns the fully
    personalised course plan with rich lesson objects.

    AI path   (no_source=True):
    Pure AI generation; the prompt uses topic + goal + ratings only.

    PDF path  (no_source=False, source_summary present):
    The prompt is additionally grounded in the PDF source structure. The AI
    follows the chapter/topic ordering from the extracted source rather than
    inventing its own structure, while still personalising lesson revision
    depth based on the student's prerequisite ratings.

    Both paths produce the same response schema so the frontend renders
    Step 3 identically for both.

    Response shape:
    {
        "course_details": { topic, goal, source },
        "prerequisites":  { "label": "rating_text", ... },
        "course_plan":    { course_name, goal, estimated_total_hours, chapters [...] }
    }
    """
    print(f"CREATE COURSE MODEL{payload.model}")
    if not payload.topic.strip():
        raise HTTPException(status_code=400, detail="Course topic is required.")
    if not payload.goal.strip():
        raise HTTPException(status_code=400, detail="Learning goal is required.")
    _assert_client()

    prereq_block = _format_prereq_block(payload.prerequisites)

    user_content = (
        f"Topic : {payload.topic}\n"
        f"Goal  : {payload.goal}\n"
        f"Source: {'AI-generated curriculum' if payload.no_source else 'PDF-sourced curriculum'}\n\n"
        f"Student Prerequisite Strengths:\n{prereq_block}\n\n"
    )

    if not payload.no_source and payload.source_summary:
        user_content += (
            "SOURCE MATERIAL (ground the chapter structure in this content):\n"
            f"{payload.source_summary[:2000]}\n\n"
        )

    user_content += (
        "Generate the full personalised course. "
        "Every lesson must open with a prerequisite_revision that addresses "
        "the student's specific weak areas identified above."
    )

    try:
        course_plan = await gateway.complete_json(
            user_content,
            model=payload.model,
            system=CreateCoursePrompt.CREATE_COURSE_SYSTEM,
            max_tokens=5000,
            temperature=0.4,
        )
    
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Model returned malformed JSON. Please retry.",
        )
    except Exception as exc:
        print(f"create course Error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    prereqs_display: Dict[str, str] = {
        key.replace("_", " ").title(): RATING_LABELS[max(1, min(4, int(val)))]
        for key, val in payload.prerequisites.items()
    }

    return {
        "course_details": {
            "topic":  payload.topic,
            "goal":   payload.goal,
            "source": "AI Generated" if payload.no_source else "PDF Uploaded",
        },
        "prerequisites": prereqs_display,
        "course_plan":   course_plan,
    }


# ════════════════════════════════════════════════════════════════════════════
# LESSON PLANNING ROUTES  (lesson_engine.py)
# ════════════════════════════════════════════════════════════════════════════

@router.post("/lesson/generate")
async def lesson_generate(payload: LessonGenerateRequest):
    """
    Convert a lesson stub from the course plan into a fully board-ready lesson.

    Calls generate_lesson() from lesson_engine.py.

    STEM-first rule: every CONCEPT_INTRODUCTION section is immediately
    followed by 2–3 WORKED_EXAMPLE sections and a practice section
    (GUIDED_PRACTICE / INDEPENDENT_PRACTICE).

    Response shape — Lesson → Sections → Steps → Events, the exact structure
    streaming_engine.py executes directly. Pass this dict unchanged as
    `teaching_script` to POST /stream/session/create:
    {
      "lesson_id":    "string",
      "lesson_title": "string",
      "subject":      "string",
      "goal":         "string",
      "key_concepts": ["string", ...],
      "sections": [
        {
          "type":    "CONCEPT_INTRODUCTION | WORKED_EXAMPLE | GUIDED_PRACTICE |
                      INDEPENDENT_PRACTICE | CHALLENGE | ...  (see lesson_engine.py)",
          "title":   "string",
          "purpose": "string",
          "steps": [
            {
              "id":        "string",
              "objective": "string",
              "events": [
                {
                  "type": "SPEAK | WRITE | HIGHLIGHT | UNDERLINE | CIRCLE |
                           ANNOTATE | ERASE | REVEAL | PAUSE | AWAIT_RESPONSE",
                  "content": "string",
                  "sync_with_previous": false
                  # true = run concurrently with the previous event in this
                  # step (e.g. WRITE while the prior SPEAK is still talking)
                }
              ]
            }
          ]
        }
      ]
    }
    """
    if not payload.lesson_title.strip():
        raise HTTPException(status_code=400, detail="lesson_title is required.")
    _assert_client()

    try:
        result = await generate_lesson(
            lesson_id             = payload.lesson_id,
            lesson_title          = payload.lesson_title,
            key_concepts          = payload.key_concepts,
            prerequisite_revision = payload.prerequisite_revision,
            description           = payload.description,
            subject               = payload.subject,
            grade_level           = payload.grade_level,
            goal                  = payload.goal,
            weak_prerequisites    = payload.weak_prerequisites,
            source_context        = payload.source_context,
            model                 = "reasoning",
        )
    except RuntimeError as exc:
        print(f"Lesson_generate RuntimeError{exc}")
        raise HTTPException(status_code=500, detail=str(exc))
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Lesson engine returned malformed JSON. Please retry.",
        )
    except Exception as exc:
        print(f"Lesson_generate Error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
    print(result)
    return result


# ════════════════════════════════════════════════════════════════════════════
# STREAMING ROUTES  (streaming_engine.py)
# ════════════════════════════════════════════════════════════════════════════

@router.post("/stream/session/create")
async def stream_session_create(payload: CreateSessionRequest):
    """
    Create a new streaming session from a lesson_engine.py lesson dict.

    Call this once after POST /lesson/generate (and optionally after
    POST /answer/anticipate for a pre-warmed question bank).

    The session starts in IDLE state. Open GET /stream/lesson to begin
    delivery. Store the returned session_id in frontend state for all
    subsequent streaming and answer calls.

    Response shape:
    {
      "session_id":     "uuid",
      "state":          "IDLE",
      "lesson_title":   "string",
      "total_sections": <int>
    }
    """
    if not payload.teaching_script:
        raise HTTPException(status_code=400, detail="teaching_script must not be empty.")

    try:
        session_id = create_session(
            teaching_script = payload.teaching_script,
            question_bank   = payload.question_bank,
        )
    except Exception as exc:
        print(f"stream_session_create Error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    # Return a minimal confirmation envelope; full state is via /stream/session/state
    state = get_session_state(session_id)

    # Fire background question-bank build the instant the session is created.
    # The lesson starts streaming NOW — we do NOT await this task before
    # returning. When /answer/ask is called mid-lesson, _resolve_question_bank()
    # inside handle_answer_session checks task.done() without ever blocking.
    # If the bank is ready → cache hit; if still building → live generation.
    _bg_anticipation_tasks[session_id] = launch_background_anticipation(
        lesson = payload.teaching_script,
    )

    return {
        "session_id":     session_id,
        "state":          state.get("state", "IDLE"),
        "lesson_title":   state.get("lesson_title", ""),
        "total_sections": state.get("total_sections", 0),
    }


@router.get("/stream/session/state")
async def stream_session_state(session_id: str = Query(...)):
    """
    Return a serializable snapshot of the session's current state.
    Safe to call at any time — does not modify state.

    Response shape:
    {
      "session_id":             "uuid",
      "state":                  "IDLE | STREAMING | PAUSED | RESUMING | COMPLETE | ERROR",
      "current_section_index":  <int>,
      "current_step_index":     <int>,
      "lesson_title":           "string",
      "total_sections":         <int>,
      "pause_context":          { segment_index, segment_type, segment_heading,
                                   step_index, last_narration, board_state_snapshot,
                                   question, pause_reason, paused_at } | null,
      "created_at":             <float>,
      "last_active_at":         <float>
    }

    Note: pause_context keeps its segment_* field names (not section_*) —
    streaming_engine.py preserves that naming for backward compatibility
    with answer_engine.py.
    """
    try:
        state = get_session_state(session_id)
    except (KeyError, ValueError):
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    except Exception as exc:
        print(f"stream_session_state Error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    return state


@router.get("/stream/lesson")
async def stream_lesson_route(session_id: str = Query(...)):
    """
    Primary SSE stream. Delivers the lesson from the session's current
    position — beginning on first call, or the paused position on resume.

    Stream event types:
      SECTION_START         — new section begins; carries type/title/purpose/
                              total_steps/requires_attempt
      STEP_START            — new step begins; carries its objective
      TEACHER_SAYS          — narration chunk (streamed word-group by word-group)
      BOARD_WRITE_START     — begin a new board line (synchronized char-by-char mode)
      BOARD_WRITE_APPEND    — append characters to the in-progress board line
      BOARD_WRITE_COMPLETE  — finalise the board line with its full content
      BOARD_WRITE           — full line reveal (non-synchronized / legacy mode)
      BOARD_HIGHLIGHT / BOARD_UNDERLINE / BOARD_CIRCLE / BOARD_ANNOTATE
                             — board annotation events
      BOARD_ERASE            — erase an expression, or "all"
      BOARD_REVEAL           — uncover previously hidden board content
      STEP_PAUSE             — silent pacing beat between board actions
      LEARNER_CHECKPOINT     — AWAIT_RESPONSE step: learner should attempt now;
                                the lesson auto-pauses right after this event
      STEP_END                — step fully delivered
      SECTION_END             — section fully delivered
      LESSON_PAUSE            — lesson paused; carries the full pause context
                                (question interrupt, or an AWAIT_RESPONSE attempt)
      LESSON_COMPLETE         — all sections delivered
      HEARTBEAT               — keep-alive for long SSE connections
      ERROR                   — stream fault; carries a message

    Events whose lesson_engine source events share sync_with_previous: true
    arrive interleaved rather than strictly sequential — e.g. BOARD_WRITE_APPEND
    chunks mixed in with TEACHER_SAYS chunks when the teacher writes while
    still talking.

    Keep the EventSource connection open until LESSON_PAUSE or LESSON_COMPLETE.
    On LESSON_PAUSE: extract pause_context from the event and open /answer/ask.
    On LESSON_COMPLETE: the lesson is finished.
    """
    try:
        get_session_state(session_id)   # validates session exists before streaming
    except (KeyError, ValueError):
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    return StreamingResponse(
        _sse_stream(stream_lesson(session_id)),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


@router.post("/stream/pause")
async def pause_stream(payload: PauseLessonRequest):
    """
    Signal the active lesson stream to pause at the next natural break point.

    The streaming engine sets a per-session asyncio.Event. The active
    delivery generators (_deliver_step / _deliver_concurrent_group) detect
    the flag between narration word-groups and board character chunks, then
    emit LESSON_PAUSE before closing the SSE stream. It always finishes the
    current atomic unit — never hangs mid-word or mid-character-chunk.

    The optional question is stored in the session's PauseContext so the
    resume bridge can reference what triggered the digression.

    After calling this, open POST /answer/ask to handle the Q&A.

    Response shape:
    {
      "paused":     true,
      "session_id": "uuid"
    }
    """
    try:
        pause_lesson(
            session_id = payload.session_id,
            question   = payload.question,
        )
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=404,
            detail=f"Session '{payload.session_id}' not found.",
        )
    except Exception as exc:
        print(f"pause_stream Error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    return {"paused": True, "session_id": payload.session_id}


@router.post("/stream/hand-raise")
async def hand_raise_stream(payload: HandRaiseRequest):
    """
    Raise the learner's hand — a soft attention request that does NOT cut
    delivery mid-word/mid-board-write the way POST /stream/pause does.

    Sequence on the active GET /stream/lesson SSE stream:
      1. HAND_RAISE_ACK fires at the next narration/board group boundary
         inside the CURRENT step — the lesson keeps playing until then; the
         frontend can show a "noted" indicator once it fires.
      2. Promotion happens at that SAME group boundary, not at STEP_END —
         groups (not steps) are the atomic unit here, same as for
         POST /stream/pause. The teacher speaks a short acknowledgement
         line, then LESSON_PAUSE fires with raised_as_hand: true in its
         payload. If the hand was raised during a step's last group,
         promotion still preempts that step's STEP_END. Same downstream
         flow as a QUESTION pause from there (open POST /answer/ask once
         the learner's question is known).

    question is optional — raise the hand first and collect the question
    once the teacher actually turns to the learner (after LESSON_PAUSE),
    or pass it here if it's already typed. Calling this again before
    promotion updates the stored question.

    Call POST /stream/hand-lower to cancel before promotion happens.

    Response shape:
    {
      "acknowledged": true | false,  ← false if the session isn't
                                         STREAMING/RESUMING right now; see
                                         "reason". No flag was set in this
                                         case — treat it the same as a
                                         failed /stream/pause call and
                                         revert any optimistic UI state.
      "session_id":   "uuid",
      "question":     "..." | null,
      "reason":       "..."          ← only present when acknowledged is false
    }
    """
    try:
        result = raise_hand(
            session_id = payload.session_id,
            question   = payload.question,
        )
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=404,
            detail=f"Session '{payload.session_id}' not found.",
        )
    except Exception as exc:
        print(f"hand_raise_stream Error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    return result


@router.post("/stream/hand-lower")
async def hand_lower_stream(payload: HandLowerRequest):
    """
    Cancel a previously raised hand before it's promoted into a pause.

    Safe to call at any time. If the hand was never raised, or was already
    promoted into a LESSON_PAUSE, this is a no-op — was_pending will be
    false in the response either way, meaning there was nothing left to
    cancel (a LESSON_PAUSE with raised_as_hand: true is likely already on
    its way, if not already delivered).

    Response shape:
    {
      "lowered":     true,
      "session_id":  "uuid",
      "was_pending": true | false   ← whether there was actually a pending
                                        raise this call cancelled
    }
    """
    try:
        result = lower_hand(session_id=payload.session_id)
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=404,
            detail=f"Session '{payload.session_id}' not found.",
        )
    except Exception as exc:
        print(f"hand_lower_stream Error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    return result


@router.get("/stream/resume")
async def resume_lesson_route(
    session_id:     str           = Query(...),
    answer_summary: Optional[str] = Query(
        None,
        description=(
            "Optional JSON-encoded summary of what was answered during the Q&A "
            "pause — { question, approach_used, question_type, core_explanation }. "
            "Helps the bridge generation reference the specific digression. "
            "Not needed for AWAIT_RESPONSE pauses (practice attempts) — omit it "
            "or pass '{}' and the bridge will acknowledge the attempt instead. "
            "If omitted entirely the engine uses the stored PauseContext alone."
        ),
    ),
):
    """
    Resume a paused lesson. Opens a new SSE stream that:
      1. Generates and streams an LLM-produced bridge phrase:
         RESUME_BRIDGE {"phase": "begin"} → TEACHER_SAYS... →
         RESUME_BRIDGE {"phase": "end"}. The bridge is always unique — never
         a template — and re-anchors the teacher naturally to where the
         lesson was paused (or acknowledges a practice attempt, for an
         AWAIT_RESPONSE pause).
      2. Delegates back into the GET /stream/lesson event stream from the
         stored section + step position.

    Call this only after POST /answer/ask returns understanding_status == CONFIRMED
    (or after the learner's AWAIT_RESPONSE attempt has been acknowledged).

    Stream event types: RESUME_BRIDGE first, then the same event types as
    GET /stream/lesson for the remainder of the stream.
    """
    # answer_summary arrives as an optional JSON string from the query parameter.
    # Parse it into a dict for streaming_engine.resume_lesson(), which expects
    # { question, approach_used, question_type, core_explanation }.
    answer_summary_dict: Dict = {}
    if answer_summary:
        try:
            answer_summary_dict = json.loads(answer_summary)
        except (json.JSONDecodeError, ValueError):
            answer_summary_dict = {}

    try:
        get_session_state(session_id)   # validates session exists before streaming
    except (KeyError, ValueError):
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    return StreamingResponse(
        _sse_stream(
            resume_lesson(
                session_id     = session_id,
                answer_summary = answer_summary_dict,
            )
        ),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


# ─── Streaming admin routes ───────────────────────────────────────────────────
@router.get("/stream/sessions")
async def list_all_sessions():
    """
    Return a lightweight summary of all in-memory sessions.
    Useful for admin dashboards and health monitoring.

    Response: list of session summary objects.
    """
    try:
        return list_sessions()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/stream/session/{session_id}")
async def evict_session_route(session_id: str):
    """
    Evict a single session from memory.

    Response shape:
    {
      "evicted":    true | false,
      "session_id": "uuid"
    }
    """
    try:
        removed = evict_session(session_id)
    except Exception as exc:
        print(f"evict_session_route Error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    # Cancel and remove the background anticipation task if one exists.
    task = _bg_anticipation_tasks.pop(session_id, None)
    if task and not task.done():
        task.cancel()

    return {"evicted": removed, "session_id": session_id}


@router.post("/stream/sessions/evict-stale")
async def evict_stale_sessions_route(payload: EvictStaleRequest):
    """
    Remove all sessions that have been idle longer than max_age_seconds.
    Call periodically (or from a background task in main.py) to prevent
    unbounded memory growth.

    Response shape:
    {
      "evicted_count":    <int>,
      "max_age_seconds":  <float>
    }
    """
    try:
        count = evict_stale_sessions(max_age_seconds=payload.max_age_seconds)
    except Exception as exc:
        print(f"evict_stale_session_route Error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    # Prune bg tasks whose session is gone (we don't have the list of evicted
    # session_ids from evict_stale_sessions, so cancel any task that's already
    # done or whose session_id is no longer registered with the streaming engine).
    stale_task_ids = [
        sid for sid, task in _bg_anticipation_tasks.items()
        if task.done() or task.cancelled()
    ]
    for sid in stale_task_ids:
        _bg_anticipation_tasks.pop(sid, None)

    return {"evicted_count": count, "max_age_seconds": payload.max_age_seconds}


# ════════════════════════════════════════════════════════════════════════════
# ANSWER ENGINE ROUTES  (answer_engine.py)
# ════════════════════════════════════════════════════════════════════════════

@router.post("/answer/anticipate")
async def answer_anticipate(payload: AnticipateRequest):
    """
    Pre-scan a teaching script and generate a full question bank.

    NOTE: In the primary lesson playback flow this endpoint is no longer a
    required serial step. /stream/session/create now fires
    launch_background_anticipation() automatically — the lesson starts
    streaming immediately while the bank builds in the background.

    This endpoint remains available as a utility for callers that want to
    build or warm a bank explicitly (e.g. pre-loading before a scheduled
    lesson, or triggering a refresh after a lesson edit).

    Response shape:
    {
      "bank_id":      "uuid",
      "lesson_title": "string",
      "subject":      "string",
      "sections": {
        "<section_id>": {
          "section_type": "...",
          "questions": [
            { "id": "...", "question": "...", "type": "WHY|HOW|...", ... }
          ]
        }
      }
    }
    """
    if not payload.teaching_script:
        raise HTTPException(status_code=400, detail="teaching_script must not be empty.")
    _assert_client()

    try:
        # NOTE: the updated answer_engine.py names this parameter `lesson` (it was
        # `teaching_script` in the prior engine version). The request body field
        # stays `teaching_script` for frontend wire compatibility — only the
        # keyword argument passed into the engine changes.
        result = await anticipate_questions(
            lesson = payload.teaching_script,
            model  = payload.model,
        )
    except RuntimeError as exc:
        print(f"answer_anticipate Error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Answer engine returned malformed JSON. Please retry.",
        )
    except Exception as exc:
        print(f"answer_anticipate Error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
    
    return result


@router.post("/answer/ask")
async def answer_ask(payload: AnswerSessionRequest):
    """
    Primary Q&A endpoint. Manages the full question-answering lifecycle.

    ── Turn 1 (initial question) ────────────────────────────────────────────
    Pass:  question, active_segment, teaching_script, session_id
    Leave: learner_response = None

    ── Turn 2+ (learner replied) ────────────────────────────────────────────
    Pass:  question, active_segment, teaching_script, session_id,
           learner_response      = "...",
           examples_given        = (from previous response),
           previous_approach     = (from previous response),
           approaches_used       = (from previous response),
           probe_question        = (from previous response — literal AWAIT_RESPONSE
                                    text; lets the engine grade a direct answer),
           seconds_since_prompt  = wall-clock seconds since the last probe fired,
           timeout_grace_used    = (from previous response),
           awaiting_final_confirmation = (from previous response — REQUIRED once
                                    true, or the learner's reply to the soft
                                    confirmation check gets misread as answering
                                    a fresh probe and the engine loops forever),
           board_state           = (from previous response),
           core_explanation      = (from previous response — feeds the resume
                                    bridge so it isn't contextless)

    ── After probe (confusion located) ─────────────────────────────────────
    Also pass confusion_location = learner's response to the probe question.

    ── Response envelope ────────────────────────────────────────────────────
    {
      "action":               "ANSWER | ESCALATE | PROBE | MICRO | RESUME",
      "payload":              { type, question, resume, sections: [...] }
                              — an event-stream envelope for ANSWER/ESCALATE/
                                PROBE/MICRO; a plain status dict for RESUME,
      "examples_given":       <int>,
      "understanding_status": "PENDING | CONFIRMED | UNCERTAIN | NOT_CONFIRMED | ESCALATED",
      "approaches_used":      ["ALGEBRAIC", "ANALOGY", ...],
      "probe_question":       "literal AWAIT_RESPONSE text, or null",
      "timeout_grace_used":   <bool>,
      "resume_lesson":        <bool>  — true only when CONFIRMED or timed out
      "awaiting_final_confirmation": <bool> — true when this payload IS the soft
                              "does that make sense" check; MUST be stored and
                              passed straight back on the next call or the
                              learner's reply gets misgraded as a fresh probe
                              answer and the confirmation check loops forever
      "board_state":          [...]
      "core_explanation":     "one-line summary of the last substantive
                               explanation, or null" — store and forward this
                               exactly like board_state; it's what lets the
                               resume bridge speak specifically instead of
                               generically once the lesson picks back up
    }

    Store examples_given, approaches_used, previous_approach, probe_question,
    timeout_grace_used, awaiting_final_confirmation, board_state, and
    core_explanation in frontend session state and forward them on every
    subsequent call. Also track wall-clock time to compute seconds_since_prompt.
    When resume_lesson is true, call GET /stream/resume — pass core_explanation
    along so the bridge prompt has real content to work with.
    """
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty.")
    if not payload.active_segment:
        raise HTTPException(status_code=400, detail="active_segment must not be empty.")
    if not payload.teaching_script:
        raise HTTPException(status_code=400, detail="teaching_script must not be empty.")
    _assert_client()

    # Resolve question bank: prefer explicit payload.question_bank, then fall
    # back to the per-session background task fired by /stream/session/create.
    # handle_answer_session / _resolve_question_bank() accept an asyncio.Task
    # directly and never block on it — if still building, it falls through to
    # live generation transparently.
    resolved_bank = payload.question_bank
    if resolved_bank is None and payload.session_id:
        resolved_bank = _bg_anticipation_tasks.get(payload.session_id)

    # Prefer the session's own record of what it actually paused on — see
    # _resolve_active_section() docstring for why the client's active_segment
    # can't always be trusted as-is.
    resolved_active_section = _resolve_active_section(
        payload.active_segment, payload.teaching_script, payload.session_id,
    )

    try:
        # NOTE: answer_engine.py renamed these two parameters
        # (active_segment → active_section, teaching_script → lesson).
        # Request body field names are kept as-is for frontend compatibility.
        result = await handle_answer_session(
            question             = payload.question,
            active_section       = resolved_active_section,
            lesson               = payload.teaching_script,
            learner_response     = payload.learner_response,
            conversation_history = payload.conversation_history,
            examples_given       = payload.examples_given,
            previous_approach    = payload.previous_approach,
            approaches_used      = payload.approaches_used,
            question_bank        = resolved_bank,
            confusion_location   = payload.confusion_location,
            probe_question       = payload.probe_question,
            seconds_since_prompt = payload.seconds_since_prompt,
            timeout_grace_used   = payload.timeout_grace_used,
            awaiting_final_confirmation = payload.awaiting_final_confirmation,
            board_state          = payload.board_state,
            core_explanation     = payload.core_explanation,
            model                = payload.model,
        )

        # If the action carries a streamable envelope AND we have a session to
        # store it in, park the envelope and tell the frontend to open /stream/answer.
        # RESUME actions never have an envelope to stream — return them as-is.
        STREAMABLE_ACTIONS = {"ANSWER", "ESCALATE", "PROBE", "MICRO"}

        if result.get("action") in STREAMABLE_ACTIONS and payload.session_id:
            store_answer_envelope(payload.session_id, result["payload"])
            # Return everything EXCEPT the heavy payload blob.
            # The frontend opens GET /stream/answer to receive the content.
            print(result)
            return {
                "action":               result["action"],
                "status":               "ready_to_stream",
                "examples_given":       result.get("examples_given", 0),
                "understanding_status": result.get("understanding_status", "PENDING"),
                "approaches_used":      result.get("approaches_used", []),
                "probe_question":       result.get("probe_question"),
                "timeout_grace_used":   result.get("timeout_grace_used", False),
                "resume_lesson":        result.get("resume_lesson", False),
                "awaiting_final_confirmation": result.get("awaiting_final_confirmation", False),
                "board_state":          result.get("board_state", []),
                "core_explanation":     result.get("core_explanation"),
            }
        
    except RuntimeError as exc:
        print(f"answer_ask RuntimeError: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Answer engine returned malformed JSON. Please retry.",
        )
    except Exception as exc:
        # Was previously print(f"answer_ask Error: {exc}") — the message alone
        # (e.g. "'str' object has no attribute 'get'") gives no file/line, so
        # every one of these required manual code review to trace. Log the
        # full traceback so future occurrences are pinpointable immediately.
        logger.exception("answer_ask Error")
        raise HTTPException(status_code=500, detail=str(exc))

    # handle_answer_session already puts the correct envelope directly in
    # result["payload"] for every action (ANSWER / ESCALATE / PROBE / MICRO /
    # RESUME). The envelope is the same event-stream shape as a lesson section
    # so streaming_engine can play it without any special-cased rendering path.
    # No flattening is needed here — just return the orchestrator result.
    print(result)
    return result


@router.post("/answer/understand")
async def answer_understand(payload: ClassifyUnderstandingRequest):
    """
    Classify a learner's reply as CONFIRMED / UNCERTAIN / NOT_CONFIRMED.

    When probe_question is supplied, the agent also grades the reply as a
    direct answer attempt (CORRECT / PARTIAL / INCORRECT / NOT_APPLICABLE)
    and includes a short spoken acknowledgment in probe_evaluation.

    This is called automatically inside POST /answer/ask on Turn 2+.
    Expose it as a standalone endpoint for cases where the frontend needs
    a lightweight classification without a full answer session turn.

    Response shape:
    {
      "status":             "CONFIRMED | UNCERTAIN | NOT_CONFIRMED | PENDING",
      "confidence":         0.0–1.0,
      "detected_signals":   ["..."],
      "recommendation":     "RESUME_LESSON | GIVE_EXAMPLE | PROBE_SPECIFIC | SIMPLIFY | WAIT",
      "follow_on_question": "extracted follow-up question, or null",
      "probe_evaluation": {
        "was_answer_attempt": true | false,
        "correctness":        "CORRECT | PARTIAL | INCORRECT | NOT_APPLICABLE",
        "acknowledgment":     "short warm spoken acknowledgment, or ''"
      }
    }
    """
    if not payload.learner_response.strip():
        raise HTTPException(status_code=400, detail="learner_response must not be empty.")
    _assert_client()

    try:
        result = await classify_understanding(
            learner_response = payload.learner_response,
            question         = payload.question,
            examples_given   = payload.examples_given,
            probe_question   = payload.probe_question,
            model            = payload.model,
        )
    except Exception as exc:
        print(f"answer_understand Error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    return result


@router.post("/answer/escalate")
async def answer_escalate(payload: EscalateRequest):
    """
    Generate a re-explanation using a completely different teaching approach.

    Called when understanding_status == NOT_CONFIRMED after an answer.
    Rotates through the approach sequence — ALGEBRAIC → ANALOGY → NUMERICAL →
    CONTRAST → BACKWARDS → STORY → VISUAL — guaranteeing a fresh perspective
    that never repeats an approach already used this session.

    Pass approaches_used from previous response envelopes so the engine
    knows which approaches are already exhausted.

    Response shape:
    {
      "action":               "ESCALATE",
      "payload":              { type, question, resume, sections: [...] },
                              — event-stream envelope; play with streaming_engine
      "approach_used":        "ALGEBRAIC | ANALOGY | NUMERICAL | ...",
      "examples_given":       <int>,
      "probe_question":       "literal AWAIT_RESPONSE text for next-turn grading",
      "understanding_status": "PENDING",
      "approaches_used":      ["ALGEBRAIC", "ANALOGY", ...]
    }
    """
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty.")
    _assert_client()

    try:
        # NOTE: answer_engine.py renamed active_segment → active_section and
        # teaching_script → lesson. Request body field names are unchanged.
        result = await escalate_with_example(
            question             = payload.question,
            active_section       = payload.active_segment,
            lesson               = payload.teaching_script,
            conversation_history = payload.conversation_history,
            example_number       = payload.example_number,
            previous_approach    = payload.previous_approach or "ALGEBRAIC",
            model                = payload.model,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Escalation engine returned malformed JSON. Please retry.",
        )
    except Exception as exc:
        print(f"answer_escalate Error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    # escalate_with_example() doesn't track approaches_used itself (handle_answer_session
    # does that bookkeeping when called via /answer/ask) — replicate the same logic here
    # so a caller hitting this endpoint directly gets a consistent running list.
    new_approaches_used = list(payload.approaches_used) + [result.get("approach_used", "")]
    return _flatten_escalation(result, approaches_used=new_approaches_used)


@router.post("/answer/probe")
async def answer_probe(payload: ProbeRequest):
    """
    Locate the learner's exact confusion point and generate a micro-explanation.

    Called after MAX_EXAMPLES have been given without a CONFIRMED understanding
    signal. Rather than blindly repeating another version of the same idea, this
    endpoint probes to find WHERE the understanding broke down, then generates a
    targeted micro-explanation addressing that specific point.

    Two-turn usage:
      Turn 1 — pass confusion_location = None.
               Response contains an event-stream envelope to play (the probe
               question as SPEAK + AWAIT_RESPONSE) plus probe_question text.
      Turn 2 — pass confusion_location = learner's answer to the probe.
               Response contains an event-stream envelope to play (the surgical
               micro-explanation) plus the follow-up confirming probe_question.

    Response shape (Turn 1 — probing):
    {
      "action":               "PROBE",
      "payload":              { type, question, resume, sections: [...] },
      "probe_question":       "literal AWAIT_RESPONSE text — forward as confusion_location on Turn 2",
      "what_answer_reveals":  { "lost_at_setup": "...", "lost_at_step": "...", "lost_overall": "..." },
      "examples_given":       <int>,
      "understanding_status": "ESCALATED"
    }

    Response shape (Turn 2 — micro-explanation):
    {
      "action":               "MICRO",
      "payload":              { type, question, resume, sections: [...] },
      "confusion_location":   "where the learner said they got lost",
      "probe_question":       "confirming AWAIT_RESPONSE text for the next understanding check",
      "understanding_status": "PENDING"
    }
    """
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty.")
    _assert_client()

    try:
        if payload.confusion_location:
            # Turn 2 — confusion located; generate a surgical micro-explanation
            # NOTE: answer_engine.py renamed active_segment → active_section and
            # teaching_script → lesson. Request body field names are unchanged.
            result = await generate_micro_explanation(
                confusion_location = payload.confusion_location,
                question           = payload.question,
                active_section     = payload.active_segment,
                lesson             = payload.teaching_script,
                model              = payload.model,
            )
        else:
            # Turn 1 — probe to locate where the confusion lives
            result = await probe_confusion_point(
                question        = payload.question,
                active_section  = payload.active_segment,
                lesson          = payload.teaching_script,
                examples_given  = payload.examples_given,
                model           = payload.model,
            )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Probe engine returned malformed JSON. Please retry.",
        )
    except Exception as exc:
        print(f"answer_probe Error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    if payload.confusion_location:
        return _flatten_micro(result)
    return _flatten_probe(result)

@router.get("/stream/answer")
async def stream_answer_route(session_id: str = Query(...)):
    """
    SSE stream for a stored answer_engine envelope.

    Open this immediately after POST /answer/ask returns
    { "status": "ready_to_stream" }.

    Replays the answer envelope through the same streaming_engine
    delivery machinery as /stream/lesson — word-by-word speech,
    character-by-character board writing, concurrent sync groups.

    Stream event types:
      SECTION_START, STEP_START, TEACHER_SAYS, BOARD_WRITE_START,
      BOARD_WRITE_APPEND, BOARD_WRITE_COMPLETE, BOARD_WRITE,
      BOARD_HIGHLIGHT, BOARD_UNDERLINE, BOARD_CIRCLE, BOARD_ANNOTATE,
      BOARD_ERASE, BOARD_REVEAL, STEP_PAUSE, LEARNER_CHECKPOINT,
      STEP_END, SECTION_END, ANSWER_COMPLETE, ERROR.

    The final LEARNER_CHECKPOINT event in the answer section IS the
    understanding probe — the frontend shows the learner's reply UI
    when it receives it, exactly as it does during GUIDED_PRACTICE.

    After ANSWER_COMPLETE, the frontend calls POST /answer/ask again
    (Turn 2+) with the learner's reply to continue the Q&A cycle,
    or waits for the learner to trigger GET /stream/resume when
    understanding_status == CONFIRMED.
    """
    try:
        get_session_state(session_id)
    except (KeyError, ValueError):
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    return StreamingResponse(
        _sse_stream(stream_answer_envelope(session_id)),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )