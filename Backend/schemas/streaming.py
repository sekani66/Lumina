# ════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS — Streaming (streaming_engine.py)
# ════════════════════════════════════════════════════════════════════════════

from typing import Optional, Dict
from pydantic import BaseModel



class CreateSessionRequest(BaseModel):
    """
    POST /stream/session/create
    Create a streaming session from a lesson_engine.py lesson dict
    (Lesson → Sections → Steps → Events — the output of POST /lesson/generate).
    The field is still named `teaching_script` for backward compatibility;
    streaming_engine.py's create_session() interprets it as the lesson_engine
    format directly.
    Optionally attach a pre-warmed question bank from POST /answer/anticipate
    to reduce latency on common questions during live delivery.
    """
    teaching_script: Dict
    question_bank:   Optional[Dict] = None


class PauseLessonRequest(BaseModel):
    """
    POST /stream/pause
    Signals the active stream to pause at the next natural break point.
    The optional question is stored in the session's PauseContext so that
    the resume bridge can reference what triggered the digression.
    """
    session_id: str
    question:   Optional[str] = None


class HandRaiseRequest(BaseModel):
    """
    POST /stream/hand-raise
    Signals a soft "raised hand" — unlike PauseLessonRequest, this does NOT
    interrupt delivery mid-word/mid-board-write. It's noticed at the next
    group boundary (HAND_RAISE_ACK) but only promoted into a real
    LESSON_PAUSE once the current step finishes cleanly (STEP_END) — the
    teacher finishes her thought, then turns to the learner, same as a
    real classroom.
    question is optional: raise the hand first and collect the question
    once the teacher actually turns to the learner (after LESSON_PAUSE
    fires with raised_as_hand: true), or pass it here if it's already
    typed. Calling this again before promotion updates the stored question.
    """
    session_id: str
    question:   Optional[str] = None


class HandLowerRequest(BaseModel):
    """
    POST /stream/hand-lower
    Cancels a previously raised hand before it's promoted into a pause —
    e.g. the learner tapped the icon by accident or changed their mind.
    Safe to call even if the hand was never raised or was already
    promoted (no-op in both cases — see was_pending in the response).
    """
    session_id: str


class EvictStaleRequest(BaseModel):
    """POST /stream/sessions/evict-stale"""
    max_age_seconds: float = 7200.0
