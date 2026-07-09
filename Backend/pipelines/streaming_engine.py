"""
Lumina Real-Time Streaming Engine
═══════════════════════════════════════════════════════════════════════════════════════
PURPOSE
  The live classroom layer.  Sits between lesson_engine.py and the learner.
  It is the teacher in the room — executing presentation events, streaming
  speech word-by-word, writing on the board character-by-character, and
  handling interruptions with warm, contextual re-entry.

  lesson_engine.py     →  plans WHAT happens (Lesson → Sections → Steps → Events)
  streaming_engine.py  →  executes it LIVE with timing, synchrony, pause/resume

═══════════════════════════════════════════════════════════════════════════════════════
WHAT HAPPENS

  this engine receives lesson_engine's four-level hierarchy and executes its presentation
  events directly.  The key capability is SYNCHRONISATION: when lesson_engine
  marks an event sync_with_previous: true, the engine runs that event concurrently
  with the previous one.  A teacher writes "x^2 + 5x + 6 = 0" on the board WHILE
  saying "Let me write this down" — not after.

  Input schema (from lesson_engine.generate_lesson()):
    lesson_engine output  →  { lesson_id, lesson_title, subject, sections: [...] }

═══════════════════════════════════════════════════════════════════════════════════════
SYNCHRONISATION MODEL

  Every presentation event from lesson_engine has sync_with_previous (bool):

    false  →  start AFTER the previous event finishes          [sequential]
    true   →  start AT THE SAME TIME as the previous event     [concurrent]

  Events are collected into "execution groups":
    • A group starts at each sync_with_previous: false event.
    • Subsequent sync_with_previous: true events join that group.

  Sequential groups are delivered one after another.
  Concurrent groups are delivered via asyncio.Task interleaving: each event
  generator runs in a background task and yields into a shared output queue.
  The result is naturally interleaved: TEACHER_SAYS chunks and BOARD_WRITE_APPEND
  chunks arrive mixed, exactly as they would in a real classroom.

  Example — teacher speaks while writing:
    [SPEAK "Let me write this down…", WRITE "x^2 + 5x + 6 = 0" (sync=true)]

  Produces an event stream like:
    TEACHER_SAYS("Let")
    BOARD_WRITE_START
    BOARD_WRITE_APPEND("x^2")
    TEACHER_SAYS("me")
    BOARD_WRITE_APPEND(" + 5")
    TEACHER_SAYS("write")
    BOARD_WRITE_APPEND("x + 6")
    TEACHER_SAYS("this")
    BOARD_WRITE_APPEND(" = 0")
    TEACHER_SAYS("down.")
    BOARD_WRITE_COMPLETE("x^2 + 5x + 6 = 0")

═══════════════════════════════════════════════════════════════════════════════════════
STREAM EVENT TYPES  (yielded to the frontend via SSE)

  ── Section / step structure ──────────────────────────────────────────────────
  SECTION_START       New section beginning; carries section metadata
  SECTION_END         Section fully delivered
  STEP_START          New step beginning; carries step objective
  STEP_END            Step fully delivered

  ── Teacher speech ────────────────────────────────────────────────────────────
  TEACHER_SAYS        Narration chunk (word-group by word-group)

  ── Board writing (WRITE events) ──────────────────────────────────────────────
  BOARD_WRITE         Full line reveal in non-sync mode
  BOARD_WRITE_START   Create an empty in-progress board line  (sync mode)
  BOARD_WRITE_APPEND  Append characters to the in-progress line (sync mode)
  BOARD_WRITE_COMPLETE  Finalise the board line with full content (sync mode)

  ── Board annotations (HIGHLIGHT / CIRCLE / UNDERLINE / ANNOTATE / ERASE / REVEAL)
  BOARD_HIGHLIGHT     Highlight existing board text
  BOARD_UNDERLINE     Underline existing board text
  BOARD_CIRCLE        Circle existing board text
  BOARD_ANNOTATE      Add an annotation label or arrow
  BOARD_ERASE         Erase expression or "all"
  BOARD_REVEAL        Uncover previously hidden content

  ── Lesson flow control ───────────────────────────────────────────────────────
  LEARNER_CHECKPOINT  Learner should attempt; lesson auto-pauses (AWAIT_RESPONSE)
  STEP_PAUSE          Silent processing beat between board actions
  LESSON_PAUSE        Lesson paused; carries full PauseContext
  RESUME_BRIDGE       Flanks the natural teacher re-entry phrase
  LESSON_COMPLETE     All sections delivered

  ── Housekeeping ──────────────────────────────────────────────────────────────
  HEARTBEAT           Keep-alive for long SSE connections
  ERROR               Stream fault; carries message

═══════════════════════════════════════════════════════════════════════════════════════
LESSON STREAM STATES

  IDLE       Session created, not yet started
  STREAMING  Actively delivering section content
  PAUSED     Mid-lesson pause (question or AWAIT_RESPONSE)
  RESUMING   Bridge being generated and streamed
  COMPLETE   All sections done
  ERROR      Unrecoverable fault

═══════════════════════════════════════════════════════════════════════════════════════
PAUSE / RESUME BEHAVIOUR

  PAUSE  — POST /stream/pause sets session._pause_flag.  The active generator
           checks this flag between word-groups (SPEAK) and between steps.
           On detection: exit early, build PauseContext, emit LESSON_PAUSE.

  RESUME — GET /stream/resume generates an LLM bridge phrase, streams it as
           TEACHER_SAYS events, then delegates back to stream_lesson() from
           the saved position.  The bridge is never a template — it reads the
           full pause context (section, step, last narration, question, answer)
           and writes natural teacher re-entry.

  AWAIT_RESPONSE — When lesson_engine places an AWAIT_RESPONSE event in a
           step (always in INDEPENDENT_PRACTICE / GUIDED_PRACTICE), the engine
           auto-pauses with PauseReason.AWAIT_RESPONSE after emitting a
           LEARNER_CHECKPOINT event.  The resume bridge is adapted to acknowledge
           the learner's attempt rather than a Q&A digression.

  RAISED HAND — POST /stream/hand-raise sets session._hand_flag (NOT
           _pause_flag).  Delivery is not interrupted mid-word/mid-group.
           At the very next GROUP boundary (i.e. as soon as whatever
           sentence/board-action was already in flight finishes — not the
           rest of the step), the raise is promoted: a HAND_RAISE_ACK SSE
           event fires (if it hasn't already for this raise), the teacher
           SPEAKS a short, warm acknowledgement line (generated in the
           background by _generate_hand_ack_bridge — kicked off at raise
           time, not promotion time, so it's ready by the time it's
           needed) via normal TEACHER_SAYS/TEACHER_AUDIO_CHUNK events,
           THEN a LESSON_PAUSE event follows with raised_as_hand: true —
           same downstream flow as a QUESTION pause from there.  Groups
           are the same atomic delivery unit _pause_flag itself respects,
           so promotion never cuts in mid-word/mid-write, it's just a
           smaller unit than a full step — a hand raised early in a long
           step doesn't wait for every remaining sentence in that step
           to play first.  POST /stream/hand-lower cancels a pending
           raise before promotion.

═══════════════════════════════════════════════════════════════════════════════════════
DELIVERY ARCHITECTURE  (two-phase, unchanged from v1)

  PHASE 1 — PREFETCH (before first SSE event)
    _prefetch_delivery_plan() fires asyncio.gather() over:
      • generate_lesson_opener()               — 1 LLM call
      • _generate_section_transition() × (N-1) — N-1 LLM calls, concurrent
    All LLM text is resolved BEFORE any event reaches the frontend.

  PHASE 2 — STREAM (pure event iterator, zero LLM calls)
    stream_lesson() reads from session.delivery_plan.
    _deliver_section() → _deliver_step() → _deliver_concurrent_group()
    → _deliver_single_event() is a pure event iterator.
    No mid-stream LLM latency, no ordering surprises.

═══════════════════════════════════════════════════════════════════════════════════════
DOWNSTREAM WIRING  (routes.py)
  GET  /stream/lesson          → stream_lesson(session_id)       [SSE]
  POST /stream/pause           → pause_lesson(session_id, ...)
  POST /stream/hand-raise      → raise_hand(session_id, ...)
  POST /stream/hand-lower      → lower_hand(session_id)
  GET  /stream/resume          → resume_lesson(session_id, ...)  [SSE]
  POST /stream/session/create  → create_session(...)
  GET  /stream/session/state   → get_session_state(session_id)
═══════════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import asyncio
import json
import random
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from pipelines import llm_gateway as gateway
from pipelines import voice_engine

from utils.streaming_engine_helpers import _strip_json

from prompts.streaming_engine_prompts import (
    _RESUME_BRIDGE_SYSTEM,
    _PRACTICE_GRADER_SYSTEM,
    _SECTION_TRANSITION_SYSTEM,
    _LESSON_OPENER_SYSTEM,
    _HAND_ACK_FALLBACKS,
    _HAND_ACK_SYSTEM,
)

# ─────────────────────────────────────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────────────────────────────────────
class LessonStreamState(str, Enum):
    IDLE       = "IDLE"
    STREAMING  = "STREAMING"
    PAUSED     = "PAUSED"
    RESUMING   = "RESUMING"
    COMPLETE   = "COMPLETE"
    ERROR      = "ERROR"


class StreamEventType(str, Enum):
    # ── Section / step structure ──────────────────────────────────────────────
    SECTION_START        = "SECTION_START"
    SECTION_END          = "SECTION_END"
    STEP_START           = "STEP_START"
    STEP_END             = "STEP_END"

    # ── Teacher speech ────────────────────────────────────────────────────────
    TEACHER_SAYS         = "TEACHER_SAYS"
    TEACHER_AUDIO_CHUNK  = "TEACHER_AUDIO_CHUNK"  # base64 PCM chunk from voice_engine
    TEACHER_AUDIO_ERROR  = "TEACHER_AUDIO_ERROR"  # non-fatal: clause fell back to silent pacing

    # ── Board writing (WRITE presentation events) ─────────────────────────────
    BOARD_WRITE          = "BOARD_WRITE"           # Full line reveal (non-sync mode)
    BOARD_WRITE_START    = "BOARD_WRITE_START"     # Create empty in-progress line
    BOARD_WRITE_APPEND   = "BOARD_WRITE_APPEND"    # Progressive chars → re-render
    BOARD_WRITE_COMPLETE = "BOARD_WRITE_COMPLETE"  # Finalise; use full content for snapshots

    # ── Board annotations ─────────────────────────────────────────────────────
    BOARD_HIGHLIGHT      = "BOARD_HIGHLIGHT"
    BOARD_UNDERLINE      = "BOARD_UNDERLINE"
    BOARD_CIRCLE         = "BOARD_CIRCLE"
    BOARD_ANNOTATE       = "BOARD_ANNOTATE"
    BOARD_ERASE          = "BOARD_ERASE"
    BOARD_REVEAL         = "BOARD_REVEAL"

    # ── Lesson flow control ───────────────────────────────────────────────────
    STEP_PAUSE           = "STEP_PAUSE"           # Silent processing beat
    LEARNER_CHECKPOINT   = "LEARNER_CHECKPOINT"   # Attempt this; lesson auto-pauses
    HAND_RAISE_ACK       = "HAND_RAISE_ACK"       # Hand noted; lesson keeps going
    LESSON_PAUSE         = "LESSON_PAUSE"
    RESUME_BRIDGE        = "RESUME_BRIDGE"
    LESSON_COMPLETE      = "LESSON_COMPLETE"

    # ── Housekeeping ──────────────────────────────────────────────────────────
    HEARTBEAT            = "HEARTBEAT"
    ERROR                = "ERROR"

    # ── Legacy aliases ────────────────────────────────────────────────────────
    SEGMENT_START        = "SEGMENT_START"         # → SECTION_START
    SEGMENT_END          = "SEGMENT_END"           # → SECTION_END
    BOARD_LINE           = "BOARD_LINE"            # → BOARD_WRITE
    BOARD_LINE_APPEND    = "BOARD_LINE_APPEND"     # → BOARD_WRITE_APPEND
    BOARD_LINE_COMPLETE  = "BOARD_LINE_COMPLETE"   # → BOARD_WRITE_COMPLETE
    BOARD_HEADING        = "BOARD_HEADING"
    BOARD_TEXT           = "BOARD_TEXT"

    ANSWER_COMPLETE = "ANSWER_COMPLETE"   # Answer envelope fully delivered


class PauseReason(str, Enum):
    QUESTION       = "QUESTION"        # Learner typed a question mid-lesson
    MANUAL         = "MANUAL"          # Learner manually paused
    TIMEOUT        = "TIMEOUT"         # No engagement signal received
    AWAIT_RESPONSE = "AWAIT_RESPONSE"  # Scripted pause for learner's attempt


# ─────────────────────────────────────────────────────────────────────────────
# DATACLASSES
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class PauseContext:
    """
    Snapshot of the lesson's exact position when a pause is triggered.
    Passed to answer_engine.py and returned to resume_lesson() as the
    answer_summary alongside any confirmed understanding data.

    Field names deliberately preserved from v1 so answer_engine and routes.py
    need no changes:
      segment_index   ← section index
      segment_type    ← section type  (CONCEPT_INTRODUCTION, WORKED_EXAMPLE…)
      segment_heading ← section title
    """
    session_id:           str
    segment_index:        int            # Section index (0-based)
    segment_type:         str            # Section type from lesson_engine
    segment_heading:      str            # Section title
    step_index:           int            # Step within the section
    last_narration:       str            # Last TEACHER_SAYS text delivered
    board_state_snapshot: List[str]      # Recent board items for context
    question:             Optional[str]
    pause_reason:         PauseReason
    paused_at:            float          # Unix timestamp
    raised_as_hand:       bool = False   # True if this pause was a hand-raise
                                          # that waited for a natural stopping
                                          # point, rather than an immediate
                                          # question interrupt. Purely informational
                                          # for resume-bridge phrasing — answer_engine
                                          # and routes.py need no changes.


@dataclass
class _LessonDeliveryPlan:
    """
    All LLM-generated content for a lesson, pre-computed BEFORE streaming begins.

    lesson_opener        — 2–3 sentence hook before section 0 begins.
    segment_transitions  — One entry per section.  [0] is always "".
                           [i] holds the transition sentence between
                           section[i-1] and section[i].
    """
    lesson_opener:        str
    segment_transitions:  List[str]


@dataclass
class StreamSession:
    """
    Live state for one lesson delivery.  One session per active learner.
    Stored in _SESSIONS keyed by session_id.

    teaching_script — holds the lesson_engine output dict directly.
    current_segment_index — tracks the SECTION index (renamed in v2 but
                            field kept for backward compat with serialised state).
    current_step_index    — tracks the STEP index within the current section.
    """
    session_id:              str
    teaching_script:         Dict          # lesson_engine output
    state:                   LessonStreamState = LessonStreamState.IDLE

    # Position tracking — updated continuously during delivery
    current_segment_index:   int           = 0   # = current section index
    current_step_index:      int           = 0
    current_group_index:     int           = 0
    last_narration:          str           = ""
    board_state:             List[str]     = field(default_factory=list)

    # Live sync signal for a WRITE running concurrently with a SPEAK (see
    # _stream_spoken_narration / voice_engine.stream_narration's "progress"
    # events). Reset at the start of each SPEAK. `elapsed_s` is the REAL
    # cumulative seconds of TTS audio produced so far; `total_estimate_s`
    # is the upfront word-model estimate for the whole narration. A
    # concurrent WRITE re-derives its remaining pace from these on every
    # chunk instead of committing to one duration guessed before either
    # side had produced anything — see _stream_board_chars_synced.
    speak_progress:          Dict[str, float] = field(
        default_factory=lambda: {"elapsed_s": 0.0, "total_estimate_s": 0.0}
    )

    # Pre-computed delivery plan.  None until _prefetch_delivery_plan() runs.
    delivery_plan:           Optional[_LessonDeliveryPlan] = None

    # Pause state
    pending_question:        Optional[str] = None
    pending_pause_reason:    Optional[PauseReason] = None
    pause_context:           Optional[PauseContext] = None

    # Pre-warmed question bank (from answer_engine.py)
    question_bank:           Optional[Dict] = None

    # Timestamps
    created_at:              float         = field(default_factory=time.time)
    paused_at:               Optional[float] = None
    last_active_at:          float         = field(default_factory=time.time)

    # Asyncio signal — set by pause_lesson(), cleared by resume_lesson()
    _pause_flag:             asyncio.Event = field(default_factory=asyncio.Event)

    pending_answer_envelope: Optional[Dict] = None   # set by store_answer_envelope()

    # ── Raised-hand state ────────────────────────────────────────────────────
    # A "raised hand" is a soft signal: the learner wants attention, but the
    # engine does NOT stop mid-word like a real pause does. It is
    # honoured at the very next GROUP boundary — the teacher finishes
    # whatever sentence/board-action is already in flight, then calls on
    # the learner right away, rather than finishing the rest of the step.
    # Set by raise_hand(), consulted and promoted entirely inside
    # _deliver_step (see _promote_hand_raise()).
    hand_raised:              bool             = False
    hand_raise_question:      Optional[str]    = None
    hand_ack_emitted:         bool             = False   # HAND_RAISE_ACK sent for this raise?
    pending_was_hand_raise:   bool             = False   # set at promotion time, read into PauseContext
    _hand_flag:               asyncio.Event    = field(default_factory=asyncio.Event)
    _hand_ack_task:           Optional[asyncio.Task] = None  # background _generate_hand_ack_bridge() call

    # Bounded history of recently generated lines, fed back into the
    # relevant prompt so its "vary your phrasing" rule has something to
    # actually check against — without this, every generation call is
    # stateless and the "don't reuse the same shape" instruction has
    # nothing to compare to, so it converges on whatever few-shot example
    # the prompt leans on hardest. RECENT_PHRASING_HISTORY_DEPTH caps how
    # far back each list looks.
    recent_hand_acks:         List[str]        = field(default_factory=list)
    recent_bridges:           List[str]        = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# IN-MEMORY SESSION STORE
# ─────────────────────────────────────────────────────────────────────────────
_SESSIONS: Dict[str, StreamSession] = {}


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# Speaking pace
NARRATION_WORDS_PER_CHUNK:  int   = 1      # Words per TEACHER_SAYS event
NARRATION_CHUNK_DELAY_S:    float = 1.80    # ≈ natural speaking pace — LEGACY FALLBACK ONLY,
                                            # used when voice narration is disabled or fails.

# Real-voice narration (voice_engine.py).  When enabled, TEACHER_SAYS pacing
# is driven by real streamed TTS audio (see _stream_spoken_narration) instead
# of NARRATION_CHUNK_DELAY_S, and TEACHER_AUDIO_CHUNK events carry the audio.
VOICE_NARRATION_ENABLED:    bool  = True
VOICE_NARRATION_VOICE:      str   = voice_engine.DEFAULT_VOICE

# Board writing (synchronized mode)
SYNC_BOARD_WRITE_CHARS:     int   = 1      # Characters per BOARD_WRITE_APPEND
SYNC_BOARD_WRITE_DELAY_S:   float = 0.20   # Motor-lag between char chunks

# Lead-in before ANY board-write activity (including the empty
# BOARD_WRITE_START slot) becomes visible, when the WRITE is running
# concurrently with a SPEAK. Without this, the empty line reserves its
# spot on the board the instant the group starts — i.e. the same frame
# the voice starts talking — before the voice has said anything the
# line could plausibly correspond to. This delay makes the board wait
# until the voice has had a beat to actually get going before the
# writing appears to "follow" it, the way a real teacher's hand trails
# slightly behind what they're saying rather than anticipating it.
SYNC_BOARD_WRITE_LEAD_IN_S: float = 1.0

# Board annotation events (HIGHLIGHT, CIRCLE, UNDERLINE, ANNOTATE)
BOARD_ACTION_DELAY_S:            float = 2.0   # Absorption pause when concurrent with SPEAK
                                               # (doesn't block anything — voice is playing
                                               # in parallel on its own task; see sync_active).
BOARD_ACTION_STANDALONE_DELAY_S: float = 0.6   # Absorption pause when this action has NO
                                               # concurrent SPEAK — i.e. it is the only thing
                                               # happening, so this delay IS dead silence.
                                               # Kept short: 0.6s of pure silence between
                                               # voice segments is what reads as an awkward,
                                               # robotic pause.

# ERASE / REVEAL feel longer than annotations
BOARD_ERASE_DELAY_S:        float = 1.0
BOARD_REVEAL_DELAY_S:       float = 0.8

# Silent PAUSE event
SILENT_PAUSE_S:             float = 0.8    # Breathing room after board content

# Turn-transition breathing room. A real teacher doesn't launch straight into
# speaking the instant they decide to turn their attention — there's a small
# physical/mental beat first. Without this, hand_ack and resume-bridge
# narration fire in the exact same instant as the ACK/BEGIN event that
# precedes them, which reads as a different, robotic process picking up
# mid-thought rather than the same teacher naturally shifting focus.
HAND_ACK_BREATH_S:          float = 0.45   # Beat before turning to a raised hand
RESUME_BRIDGE_BREATH_S:     float = 0.70   # Beat before re-engaging after a Q&A digression

# Inter-step and inter-section gaps
BETWEEN_STEP_DELAY_S:       float = 0.8    # After STEP_END before next STEP_START
BETWEEN_SECTION_DELAY_S:    float = 1.0    # Let SECTION_END land; board clears

# Synchronized board reveal flag
# True  — board lines are written char-by-char concurrent with speech.
# False — board lines appear all at once (legacy / low-latency mode).
SYNCHRONIZED_BOARD_REVEAL:  bool  = True

# Board snapshot depth for PauseContext
BOARD_SNAPSHOT_DEPTH:       int   = 5

# How many recently generated lines to remember per category (hand-acks,
# resume bridges) and feed back into the next prompt so "vary your
# phrasing" is something the model can actually check against, instead of
# an instruction with no memory behind it.
RECENT_PHRASING_HISTORY_DEPTH: int = 5


def _format_recent_lines(lines: List[str]) -> str:
    """
    Render a session's recent-lines history as a prompt block, or "" if
    empty (first use of the lesson — nothing to avoid yet).
    """
    if not lines:
        return ""
    rendered = "\n".join(f'  - "{ln}"' for ln in lines)
    return (
        "\nRECENTLY USED LINES (do not repeat this shape or opening word):\n"
        f"{rendered}\n"
    )


def _remember_line(history: List[str], line: str) -> None:
    """Append `line` to a bounded recent-lines history, in place."""
    if not line:
        return
    history.append(line)
    del history[:-RECENT_PHRASING_HISTORY_DEPTH]


# Heartbeat interval for long SSE connections
HEARTBEAT_INTERVAL_S:       float = 8.0


# ─────────────────────────────────────────────────────────────────────────────
# PRIVATE LANGUAGE-LEVEL HELPERS
# ─────────────────────────────────────────────────────────────────────────────
async def _llm(
    system:      str,
    user:        str,
    model:       Optional[str]   = None,
    temperature: float = 0.7,
    max_tokens:  int   = 400,
) -> str:
    """Single LLM call returning raw text. Used for bridge + transitions."""
    try:
        return await gateway.complete(
            user,
            model=model,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except gateway.LLMGatewayError as exc:
        if "truncated" in str(exc).lower():
            raise RuntimeError(
                "Streaming engine response was truncated (response exceeded "
                "max_tokens). Reduce max_tokens or simplify the prompt and retry."
            ) from exc
        raise RuntimeError(str(exc)) from exc


async def _stream_text_chunks(
    text:            str,
    words_per_chunk: int   = NARRATION_WORDS_PER_CHUNK,
    delay_s:         float = NARRATION_CHUNK_DELAY_S,
) -> AsyncGenerator[str, None]:
    """
    Yield pre-written text in small word groups with pacing delays.
    Gives the word-by-word speaking effect for TEACHER_SAYS delivery.
    Not an LLM call — pure chunked delivery of known text.
    """
    words = text.split()
    for i in range(0, len(words), words_per_chunk):
        yield " ".join(words[i : i + words_per_chunk])
        await asyncio.sleep(delay_s)


async def _stream_spoken_narration(
    text:      str,
    session:   StreamSession,
    sec_idx:   int,
    sec_type:  str,
    step_idx:  int,
    role:      Optional[str] = None,
) -> AsyncGenerator[Dict, None]:
    """
    Stream one narration string as SSE events, using voice_engine's real TTS
    audio as the pacing clock instead of a fixed per-word sleep.

    Emits TEACHER_SAYS the instant voice_engine says a word is due (i.e. the
    real audio has reached that word's onset), interleaved with
    TEACHER_AUDIO_CHUNK events carrying the base64 PCM the frontend should
    actually play. A per-clause TTS failure inside voice_engine already
    degrades to silent, evenly-paced words (see voice_engine's own
    FAILURE MODE) — we surface that as a non-fatal TEACHER_AUDIO_ERROR here
    so the caller can log/observe it, without interrupting the lesson.

    Falls back entirely to the legacy fixed-pace _stream_text_chunks() when
    VOICE_NARRATION_ENABLED is False, or if voice_engine raises before
    producing anything at all (e.g. it couldn't be reached).

    Pause checks for the text-only (no-TTS) fallback path happen between
    words, same as before — there's no audio to protect there.

    For the real-voice path, the pause flag is instead passed to
    voice_engine.stream_narration as `stop_check`, which only polls it
    BETWEEN clauses.
    """
    if not VOICE_NARRATION_ENABLED:
        async for chunk in _stream_text_chunks(text):
            session.last_narration = chunk
            yield _build_event(
                StreamEventType.TEACHER_SAYS,
                {"content": chunk, "render": "none", "role": role, "step_index": step_idx},
                sec_idx, sec_type, step_idx,
            )
            if session._pause_flag.is_set():
                return
        return

    # Reset the live sync clock for this narration. A concurrently-running
    # WRITE (see _stream_board_chars_synced) reads this dict on every
    # chunk it emits, so it needs to start from zero here rather than
    # carrying over whatever the previous SPEAK left behind.
    session.speak_progress = {"elapsed_s": 0.0, "total_estimate_s": 0.0}

    try:
        async for item in voice_engine.stream_narration(
            text, role=role, voice=VOICE_NARRATION_VOICE,
            stop_check=lambda: session._pause_flag.is_set(),
        ):
            kind = item.get("kind")

            if kind == "progress":
                # Internal sync signal only — never forwarded to the
                # frontend. This is the fix for the WRITE/SPEAK desync:
                # a concurrent BOARD_WRITE reads session.speak_progress
                # live instead of a duration estimated once upfront.
                if "elapsed_s" in item:
                    session.speak_progress["elapsed_s"] = item["elapsed_s"]
                if "total_estimate_s" in item:
                    session.speak_progress["total_estimate_s"] = item["total_estimate_s"]
                continue

            if kind == "word":
                session.last_narration = item["text"]
                yield _build_event(
                    StreamEventType.TEACHER_SAYS,
                    {"content": item["text"], "render": "none", "role": role, "step_index": step_idx},
                    sec_idx, sec_type, step_idx,
                )

            elif kind == "audio":
                yield _build_event(
                    StreamEventType.TEACHER_AUDIO_CHUNK,
                    {
                        "data":        item["data"],
                        "format":      item["format"],
                        "sample_rate": item["sample_rate"],
                        "step_index":  step_idx,
                    },
                    sec_idx, sec_type, step_idx,
                )

            elif kind == "audio_error":
                yield _build_event(
                    StreamEventType.TEACHER_AUDIO_ERROR,
                    {"message": item.get("message", ""), "step_index": step_idx},
                    sec_idx, sec_type, step_idx,
                )

    except Exception as exc:  # noqa: BLE001 — voice_engine failed to start;
        # fall back so the lesson still narrates (silently) instead of dying.
        yield _build_event(
            StreamEventType.TEACHER_AUDIO_ERROR,
            {"message": str(exc), "step_index": step_idx},
            sec_idx, sec_type, step_idx,
        )
        async for chunk in _stream_text_chunks(text):
            session.last_narration = chunk
            yield _build_event(
                StreamEventType.TEACHER_SAYS,
                {"content": chunk, "render": "none", "role": role, "step_index": step_idx},
                sec_idx, sec_type, step_idx,
            )
            if session._pause_flag.is_set():
                return


async def _stream_board_chars(
    text:            str,
    chars_per_chunk: int   = SYNC_BOARD_WRITE_CHARS,
    delay_s:         float = SYNC_BOARD_WRITE_DELAY_S,
) -> AsyncGenerator[str, None]:
    """
    Yield board content in small character groups with motor-lag delays.
    Gives the character-by-character writing animation for BOARD_WRITE_APPEND.

    LaTeX expressions like \\frac{…}{…} are written as-is; the frontend
    re-renders the KaTeX partial string on every append event, producing a
    natural "chalk appearing on the board" effect.
    """
    for i in range(0, len(text), chars_per_chunk):
        yield text[i : i + chars_per_chunk]
        await asyncio.sleep(delay_s)


async def _stream_board_chars_synced(
    text:      str,
    session:   StreamSession,
    lead_in_s: float = 1.5,
) -> AsyncGenerator[str, None]:
    """
    Char-by-char board reveal paced against the REAL, live speech clock
    (session.speak_progress) instead of one delay_s computed before either
    side had produced anything.
    
    Every chunk, re-read how much real audio has ACTUALLY elapsed
    (session.speak_progress["elapsed_s"], driven by real bytes received —
    see voice_engine._speak_clause) and how much total narration time is
    estimated (session.speak_progress["total_estimate_s"]), then re-derive
    the remaining per-char delay from what's actually left. This is a
    closed-loop pacer, not a one-shot guess: if speech runs faster or
    slower than the estimate, the very next chunk's delay corrects for it,
    instead of the drift accumulating silently for the rest of the clause.
    """
    await asyncio.sleep(lead_in_s)

    total_chars = len(text)
    if total_chars == 0:
        return
    written = 0

    while written < total_chars:
        progress         = session.speak_progress
        total_estimate_s = progress.get("total_estimate_s") or 0.0
        elapsed_s        = progress.get("elapsed_s") or 0.0

        speech_still_running = elapsed_s < total_estimate_s
        if speech_still_running:
            remaining_s     = max(0.05, total_estimate_s - elapsed_s)
            remaining_chars = total_chars - written
            delay_s = max(0.05, min(0.5, remaining_s / remaining_chars))
        else:
            # The paired speech has already finished — there's no live clock
            # left to sync against. Fall back to a fixed, natural writing
            # pace instead of racing to the floor and flashing the line in.
            delay_s = SYNC_BOARD_WRITE_DELAY_S 

        yield text[written]
        written += 1
        await asyncio.sleep(delay_s)


def _build_event(
    event_type:    StreamEventType,
    payload:       Optional[Dict] = None,
    segment_index: Optional[int]  = None,
    segment_type:  Optional[str]  = None,
    step_index:    Optional[int]  = None,
) -> Dict:
    """
    Construct a stream event dict for the frontend.
    Every event yielded by the SSE stream passes through here.

    Shape:
      {
        "event":   "TEACHER_SAYS",
        "payload": { ... },
        "meta": {
          "segment_index": 2,
          "segment_type":  "CONCEPT_INTRODUCTION",
          "step_index":    1,
          "ts":            1718123456.789
        }
      }
    """
    return {
        "event":   event_type.value,
        "payload": payload or {},
        "meta": {
            "segment_index": segment_index,
            "segment_type":  segment_type,
            "step_index":    step_index,
            "ts":            time.time(),
        },
    }


def _get_session(session_id: str) -> StreamSession:
    """Retrieve a session or raise ValueError if not found."""
    session = _SESSIONS.get(session_id)
    if session is None:
        raise ValueError(f"Session not found: {session_id}")
    return session


def _save_session(session: StreamSession) -> None:
    """Persist session.  Swap for a Redis write in production."""
    _SESSIONS[session.session_id] = session
    session.last_active_at = time.time()


def _track_board_state(session: StreamSession, content: Any) -> None:
    """
    Append a revealed board item to the session's rolling board-state buffer.
    Used to populate PauseContext.board_state_snapshot.
    """
    session.board_state.append(str(content))
    if len(session.board_state) > BOARD_SNAPSHOT_DEPTH * 2:
        session.board_state = session.board_state[-BOARD_SNAPSHOT_DEPTH:]


def _is_latex_content(text: str) -> bool:
    """
    Return True if the text looks like KaTeX/LaTeX markup.
    Detects: backslash commands, superscript ^, subscript _, braces {}, $ signs.
    """
    return bool(re.search(r'[\\^_{$}]', text))


def _build_script_summary(lesson: Dict) -> str:
    """One-line lesson summary injected into LLM prompts for context."""
    return (
        f"Lesson: {lesson.get('lesson_title', '')} | "
        f"Subject: {lesson.get('subject', '')} | "
        f"Goal: {lesson.get('goal', '')}"
    )


def _format_pause_context_for_prompt(pause_ctx: PauseContext) -> str:
    """Render PauseContext as human-readable text for LLM context injection."""
    lines = [
        f"Lesson position : Section {pause_ctx.segment_index} "
        f"({pause_ctx.segment_type}) — Step {pause_ctx.step_index}",
        f"Section title   : {pause_ctx.segment_heading}",
        f"Last thing said : {pause_ctx.last_narration or '(opening narration)'}",
        f"Board at pause  : {' | '.join(pause_ctx.board_state_snapshot) or '(empty)'}",
        f"Pause reason    : {pause_ctx.pause_reason.value}",
        f"Question asked  : {pause_ctx.question or '(no question — attempt pause)'}",
    ]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# CONCURRENT EVENT INFRASTRUCTURE
# ─────────────────────────────────────────────────────────────────────────────
def _group_events_by_sync(events: List[Dict]) -> List[List[Dict]]:
    """
    Split a step's event list into execution groups based on sync_with_previous.

    A new group starts at each event with sync_with_previous: false.
    Subsequent events with sync_with_previous: true are appended to the
    current group and run concurrently with it.

    Exception — WRITE events: a WRITE may sync with a preceding SPEAK or
    visual event (CIRCLE, HIGHLIGHT, etc.) but NEVER with another WRITE.
    The BOARD_WRITE_START/APPEND/COMPLETE protocol carries no line identifier,
    so two concurrent WRITEs produce interleaved APPEND chunks the client
    cannot assign to the correct slot — one line freezes mid-char and the
    other is lost entirely.

    Exception — AWAIT_RESPONSE / PAUSE: these are isolated on BOTH sides,
    not just kept from joining the group before them. AWAIT_RESPONSE's own
    delivery is synchronous (it sets session._pause_flag almost instantly),
    so anything that ends up sharing its group — a SPEAK still narrating,
    a WRITE still writing — sees the pause flag flip mid-stream and bails
    out right there: SPEAK cuts the voice off mid-sentence, and WRITE breaks
    its char-loop but then still emits BOARD_WRITE_COMPLETE with the FULL
    content (so the board visibly jumps to "done" at the exact moment the
    voice goes silent). A trailing event marked sync_with_previous: true
    would otherwise slide straight into AWAIT_RESPONSE's group and race it
    this way — so the isolation has to hold for whatever comes right after
    it too, not just what came before.

    Example:
      SPEAK(sync=F), WRITE(sync=T), WRITE(sync=T), PAUSE(sync=F)
      → [[SPEAK, WRITE], [WRITE], [PAUSE]]
    """
    groups: List[List[Dict]] = []
    current: List[Dict] = []
    isolate_next = False  # True right after an AWAIT_RESPONSE/PAUSE — the
                           # next event may not join that group even if it
                           # declares sync_with_previous: true.

    for event in events:
        ev_type = event.get("type")
        # ANNOTATE (and REVEAL) are isolated like AWAIT_RESPONSE/PAUSE: their
        # Lesson.jsx(lesson board page) handlers `await pushAndReveal(...)`, a real animated
        # reveal that runs for the full per-line pacing duration. If either
        # shares a concurrent group with a WRITE, the interleaved SSE stream
        # can deliver the ANNOTATE/REVEAL event first, and the frontend's
        # sequential event loop then blocks on that reveal for the whole
        # group — every BOARD_WRITE_APPEND/COMPLETE behind it sits stuck in
        # the queue and only flushes once the reveal (and any further
        # blocking events after it) finally resolve. Unlike HIGHLIGHT/CIRCLE/
        # UNDERLINE, whose handlers are synchronous, ANNOTATE and REVEAL are
        # not safe to run concurrently with anything.
        force_sequential = (
            ev_type in ("AWAIT_RESPONSE", "PAUSE", "ANNOTATE", "REVEAL")
            or isolate_next
        )
        # Prevent two WRITE events sharing a concurrent group.
        if ev_type == "WRITE" and any(e.get("type") == "WRITE" for e in current):
            force_sequential = True

        # Prevent two SPEAK events sharing a concurrent group — each SPEAK
        # opens its own real TTS stream (voice_engine.stream_narration).
        # Two concurrent SPEAKs mean two live voices talking over each
        # other, not one teacher speaking continuously. sync_with_previous
        # on a second SPEAK should mean "no pause before this," not
        # "play simultaneously" — force it into a new sequential group.
        if ev_type == "SPEAK" and any(e.get("type") == "SPEAK" for e in current):
            force_sequential = True

        is_sync = event.get("sync_with_previous", False) and not force_sequential

        if not is_sync and current:
            groups.append(current)
            current = []
        current.append(event)

        isolate_next = ev_type in ("AWAIT_RESPONSE", "PAUSE", "ANNOTATE", "REVEAL")
    if current:
        groups.append(current)
    return groups

async def _interleave(*generators: AsyncGenerator) -> AsyncGenerator[Dict, None]:
    """
    Run multiple async generators concurrently and yield their outputs
    interleaved in arrival order.

    Each generator is wrapped in an asyncio.Task that drains it into a
    shared output queue.  The caller sees a single merged stream — exactly
    as if all generators were running side-by-side.  This is the mechanism
    that makes SPEAK and WRITE events arrive interleaved when they share
    a concurrent execution group.

    Cleanup: all tasks are cancelled on exit (including on exception).
    """
    _DONE = object()
    queue: asyncio.Queue = asyncio.Queue()
    done_count = 0
    total = len(generators)

    async def _drain(gen: AsyncGenerator) -> None:
        nonlocal done_count
        try:
            async for item in gen:
                await queue.put(item)
        finally:
            done_count += 1
            await queue.put(_DONE)

    tasks = [asyncio.create_task(_drain(gen)) for gen in generators]
    received_done = 0

    try:
        while received_done < total:
            item = await queue.get()
            if item is _DONE:
                received_done += 1
            else:
                yield item
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()


# ─────────────────────────────────────────────────────────────────────────────
# SINGLE EVENT DELIVERY
# ─────────────────────────────────────────────────────────────────────────────
async def _deliver_single_event(
    event:     Dict,
    session:   StreamSession,
    sec_idx:   int,
    sec_type:  str,
    step_idx:  int,
    sync_active: bool = False,
) -> AsyncGenerator[Dict, None]:
    """
    Execute one presentation event from lesson_engine and yield the resulting
    SSE events.

    Each lesson_engine event type maps to one or more SSE event types:

      SPEAK          → TEACHER_SAYS (word by word)
      WRITE          → BOARD_WRITE_START + BOARD_WRITE_APPEND(s) + BOARD_WRITE_COMPLETE
                       (or BOARD_WRITE in non-sync mode)
      HIGHLIGHT      → BOARD_HIGHLIGHT
      UNDERLINE      → BOARD_UNDERLINE
      CIRCLE         → BOARD_CIRCLE
      ANNOTATE       → BOARD_ANNOTATE
      ERASE          → BOARD_ERASE
      REVEAL         → BOARD_REVEAL
      PAUSE          → STEP_PAUSE  (+ asyncio.sleep)
      AWAIT_RESPONSE → LEARNER_CHECKPOINT  (auto-pause triggered after)

    Pause checks are performed between word-groups (SPEAK) and between
    character chunks (WRITE).  Other event types are near-instant and do
    not themselves check the flag — they are too short to interrupt usefully.
    """
    ev_type = event.get("type", "")
    # Use `or ""` only as a safe default; WRITE events validate content below.
    content = event.get("content") or ""

    # ── SPEAK ─────────────────────────────────────────────────────────────────
    if ev_type == "SPEAK":
        # role defaults to "explanation" — lesson_engine may stamp its own
        # role onto the event; fall back to the measured, mid-derivation
        # register otherwise (see voice_engine._INSTRUCTION_PRESETS).
        speak_role = event.get("role", "explanation")
        # No pause-check-and-return here: doing so would force this
        # generator closed while _stream_spoken_narration (and, beneath
        # it, voice_engine.stream_narration) is mid-clause — the exact
        # GeneratorExit-cancels-the-TTS-task cutoff bug this file used to
        # have. voice_engine now stops itself at the next clause boundary
        # once session._pause_flag is set (passed through as
        # stop_check), so this loop already ends on its own as soon as
        # that's safe to do. Callers of _deliver_single_event (e.g.
        # _deliver_step) re-check the flag after this event returns.
        async for ev in _stream_spoken_narration(
            content, session, sec_idx, sec_type, step_idx, role=speak_role
        ):
            yield ev

    # ── WRITE ─────────────────────────────────────────────────────────────────
    elif ev_type == "WRITE":
        # Guard: a null or empty WRITE emits BOARD_WRITE_START/COMPLETE with
        # empty content, which reserves a blank slot on the board (the silent
        # gap bug).  Skip it rather than writing an invisible line.
        if not content.strip():
            return

        render = "latex" if _is_latex_content(content) else "text"

        if SYNCHRONIZED_BOARD_REVEAL:
            if sync_active:
                # Wait BEFORE anything appears on the board at all — not
                # just before the chars start filling in. Previously
                # BOARD_WRITE_START (the empty line slot) fired the
                # instant this group started, i.e. the same beat the
                # voice started talking, before the voice had said
                # anything the line could correspond to. Now the board
                # stays untouched until the voice has had a beat to get
                # going, so writing visibly follows the voice instead of
                # anticipating it.
                await asyncio.sleep(SYNC_BOARD_WRITE_LEAD_IN_S)

            # Char-by-char writing — the concurrent board animation
            yield _build_event(
                StreamEventType.BOARD_WRITE_START,
                {"content": "", "render": render, "step_index": step_idx},
                sec_idx, sec_type, step_idx,
            )

            if sync_active:
                # Paced against the REAL, live speech clock — see
                # _stream_board_chars_synced for why this replaced a
                # single upfront duration estimate. The lead-in already
                # happened above, so no further lead-in here.
                char_source = _stream_board_chars_synced(content, session, lead_in_s=0.0)
            else:
                char_source = _stream_board_chars(
                    content, SYNC_BOARD_WRITE_CHARS, SYNC_BOARD_WRITE_DELAY_S
                )

            async for chars in char_source:
                yield _build_event(
                    StreamEventType.BOARD_WRITE_APPEND,
                    {"content": chars, "render": render, "step_index": step_idx},
                    sec_idx, sec_type, step_idx,
                )
                if session._pause_flag.is_set():
                    break
            # Always complete the line so the board state is consistent,
            # even if we were interrupted mid-write.
            yield _build_event(
                StreamEventType.BOARD_WRITE_COMPLETE,
                {"content": content, "render": render, "step_index": step_idx},
                sec_idx, sec_type, step_idx,
            )
        else:
            # Instant full reveal (legacy mode)
            yield _build_event(
                StreamEventType.BOARD_WRITE,
                {"content": content, "render": render, "step_index": step_idx},
                sec_idx, sec_type, step_idx,
            )

        _track_board_state(session, content)

    # ── HIGHLIGHT ─────────────────────────────────────────────────────────────
    elif ev_type == "HIGHLIGHT":
        yield _build_event(
            StreamEventType.BOARD_HIGHLIGHT,
            {"content": content, "step_index": step_idx},
            sec_idx, sec_type, step_idx,
        )
        await asyncio.sleep(BOARD_ACTION_DELAY_S if sync_active else BOARD_ACTION_STANDALONE_DELAY_S)

    # ── UNDERLINE ─────────────────────────────────────────────────────────────
    elif ev_type == "UNDERLINE":
        yield _build_event(
            StreamEventType.BOARD_UNDERLINE,
            {"content": content, "step_index": step_idx},
            sec_idx, sec_type, step_idx,
        )
        await asyncio.sleep(BOARD_ACTION_DELAY_S if sync_active else BOARD_ACTION_STANDALONE_DELAY_S)

    # ── CIRCLE ────────────────────────────────────────────────────────────────
    elif ev_type == "CIRCLE":
        yield _build_event(
            StreamEventType.BOARD_CIRCLE,
            {"content": content, "step_index": step_idx},
            sec_idx, sec_type, step_idx,
        )
        await asyncio.sleep(BOARD_ACTION_DELAY_S if sync_active else BOARD_ACTION_STANDALONE_DELAY_S)

    # ── ANNOTATE ──────────────────────────────────────────────────────────────
    elif ev_type == "ANNOTATE":
        render = "latex" if _is_latex_content(content) else "text"
        yield _build_event(
            StreamEventType.BOARD_ANNOTATE,
            {"content": content, "render": render, "step_index": step_idx},
            sec_idx, sec_type, step_idx,
        )
        await asyncio.sleep(BOARD_ACTION_DELAY_S if sync_active else BOARD_ACTION_STANDALONE_DELAY_S)

    # ── ERASE ─────────────────────────────────────────────────────────────────
    elif ev_type == "ERASE":
        target = content or "all"
        yield _build_event(
            StreamEventType.BOARD_ERASE,
            {"content": target, "step_index": step_idx},
            sec_idx, sec_type, step_idx,
        )
        if target == "all":
            session.board_state.clear()
        await asyncio.sleep(BOARD_ERASE_DELAY_S)

    # ── REVEAL ────────────────────────────────────────────────────────────────
    elif ev_type == "REVEAL":
        yield _build_event(
            StreamEventType.BOARD_REVEAL,
            {"content": content, "step_index": step_idx},
            sec_idx, sec_type, step_idx,
        )
        _track_board_state(session, content)
        await asyncio.sleep(BOARD_REVEAL_DELAY_S)

    # ── PAUSE  (silent beat) ──────────────────────────────────────────────────
    elif ev_type == "PAUSE":
        yield _build_event(
            StreamEventType.STEP_PAUSE,
            {"delay_ms": int(SILENT_PAUSE_S * 1000), "step_index": step_idx},
            sec_idx, sec_type, step_idx,
        )
        await asyncio.sleep(SILENT_PAUSE_S)

    # ── AWAIT_RESPONSE  (scripted practice pause) ─────────────────────────────
    elif ev_type == "AWAIT_RESPONSE":
        #  Signal the frontend to show the attempt UI.
        yield _build_event(
            StreamEventType.LEARNER_CHECKPOINT,
            {
                "content":      content or "Attempt this problem before continuing.",
                "section_type": sec_type,
                "step_index":   step_idx,
            },
            sec_idx, sec_type, step_idx,
        )
        # Auto-pause: set the flag so the stream exits cleanly at the next
        # pause-flag check (between groups in _deliver_step).  The lesson
        # waits here until the learner submits their attempt and resume_lesson()
        # clears the flag.
        if not session._pause_flag.is_set():
            session.pending_question     = content
            session.pending_pause_reason = PauseReason.AWAIT_RESPONSE
            session._pause_flag.set()
            _save_session(session)


# ─────────────────────────────────────────────────────────────────────────────
# CONCURRENT GROUP, STEP, AND SECTION DELIVERY
# ─────────────────────────────────────────────────────────────────────────────

async def _deliver_concurrent_group(
    events:   List[Dict],
    session:  StreamSession,
    sec_idx:  int,
    sec_type: str,
    step_idx: int,
) -> AsyncGenerator[Dict, None]:
    """
    Deliver a group of presentation events.

    Single-event group → delivered sequentially (the common case).

    Multi-event group  → all events are run concurrently via asyncio tasks,
                         and their SSE outputs are interleaved in arrival order.

    This is the synchronisation engine.  When lesson_engine marks a WRITE
    event sync_with_previous: true after a SPEAK event, both end up in the
    same group and their word-chunks and char-chunks arrive interleaved — the
    frontend receives them as one blended stream of board + voice activity,
    exactly like a teacher speaking while writing.

    A companion WRITE in the group paces itself off the SPEAK's REAL,
    live audio clock (session.speak_progress), not a duration estimated
    once upfront here — see _stream_board_chars_synced for why that
    upfront estimate was the source of the WRITE/SPEAK desync.
    """
    has_speak = any(e.get("type") == "SPEAK" for e in events)

    if len(events) == 1:
        async for ev in _deliver_single_event(
            events[0], session, sec_idx, sec_type, step_idx
        ):
            yield ev
        return

    # Build a generator for each concurrent event
    generators = [
        _deliver_single_event(ev, session, sec_idx, sec_type, step_idx, sync_active=has_speak)
        for ev in events
    ]
    async for ev in _interleave(*generators):
        yield ev


async def _promote_hand_raise(
    session:  StreamSession,
    sec_idx:  int,
    sec_type: str,
    step_idx: int,
) -> AsyncGenerator[Dict, None]:
    """
    Speak the acknowledgement line and promote a raised hand into a real
    pause.  Called at the very next GROUP boundary after a hand was
    raised — i.e. as soon as whatever sentence/board-action was already
    in flight finishes, not the rest of the step. Groups are the same
    atomic delivery unit _pause_flag itself respects, so this never cuts
    in mid-word/mid-write; it's just a smaller unit than a full step.

    Emits HAND_RAISE_ACK first if it hasn't already fired for this raise
    (it may already have, from an earlier group boundary in this same
    step), then the spoken acknowledgement line, then sets the pause
    flag. Does NOT emit LESSON_PAUSE itself — that's built by
    stream_lesson() once this generator's caller unwinds back up to it.
    """
    if not session.hand_ack_emitted:
        session.hand_ack_emitted = True
        yield _build_event(
            StreamEventType.HAND_RAISE_ACK,
            {"question": session.hand_raise_question},
            sec_idx, sec_type, step_idx,
        )

    ack_text = await _resolve_hand_ack_text(session)

    # Beat before speaking — see HAND_ACK_BREATH_S. Without this, the ack
    # fires the instant the group boundary is hit, landing in the same
    # breath as whatever was already being said.
    await asyncio.sleep(HAND_ACK_BREATH_S)

    async for ev in _stream_spoken_narration(
        ack_text, session, sec_idx, sec_type, step_idx, role="hand_ack",
    ):
        yield ev

    session.pending_question       = session.hand_raise_question
    session.pending_pause_reason   = PauseReason.QUESTION
    session.pending_was_hand_raise = True
    session.hand_raised            = False
    session.hand_ack_emitted       = False
    session.hand_raise_question    = None
    session._hand_flag.clear()
    session._pause_flag.set()


async def _deliver_step(
    step:      Dict,
    session:   StreamSession,
    sec_idx:   int,
    sec_type:  str,
    step_idx:  int,
    start_group: int =0,
) -> AsyncGenerator[Dict, None]:
    """
    Deliver a single step by executing its presentation events in order,
    respecting sync_with_previous for concurrent groups.

    Delivery order:
      STEP_START
      For each execution group (sequential):
        [pause check]
        [raised-hand promotion check — see below]
        → _deliver_concurrent_group (single or interleaved events)
        [pause check between groups]
      [raised-hand promotion check for a hand raised during the FINAL group]
      STEP_END  (only if not interrupted)

    If the pause flag fires during a group, execution stops at the next
    word-boundary (SPEAK) or char-boundary (WRITE).  The step will be
    re-delivered from the start on resume — events within a step form a
    cohesive teaching moment and are not split across a pause.

    A raised hand is promoted into a real pause at the very next group
    boundary — not the step boundary. Groups are the atomic unit here
    (same as for _pause_flag), so this still never interrupts a
    still-in-flight sentence or board-write; it just doesn't wait for
    every remaining sentence in the step to finish first, the way waiting
    for STEP_END would.
    """
    events = step.get("events", [])
    if not events:
        return

    yield _build_event(
        StreamEventType.STEP_START,
        {
            "step_index": step_idx,
            "step_id":    step.get("id", f"step_{step_idx}"),
            "objective":  step.get("objective", ""),
        },
        sec_idx, sec_type, step_idx,
    )

    groups = _group_events_by_sync(events)

    for group_indx, group in enumerate(groups):
        if group_indx < start_group:
            continue #skip already delivered groups

        if session._pause_flag.is_set():
            session.current_group_index = group_indx  #resume FROM here
            return

        if session._hand_flag.is_set():
            async for ev in _promote_hand_raise(session, sec_idx, sec_type, step_idx):
                yield ev
            session.current_group_index = group_indx  # this group hasn't played — resume FROM here
            return

        async for ev in _deliver_concurrent_group(
            group, session, sec_idx, sec_type, step_idx
        ):
            yield ev

        if session._pause_flag.is_set():
            session.current_group_index = group_indx + 1 # group done? resume AFTER it
            return

    # Catch a hand raised during delivery of the FINAL group — the in-loop
    # boundary check above only runs at the START of an iteration, so a
    # raise that happens while the last group is playing has no further
    # iteration to be caught by.
    if session._hand_flag.is_set():
        async for ev in _promote_hand_raise(session, sec_idx, sec_type, step_idx):
            yield ev
        session.current_group_index = len(groups)
        return  # current_group_index already 0 — resume starts the NEXT step fresh
    
    session.current_group_index = 0

    # Only emit STEP_END if we weren't interrupted
    yield _build_event(
        StreamEventType.STEP_END,
        {"step_index": step_idx},
        sec_idx, sec_type, step_idx,
    )


async def _deliver_section(
    section:    Dict,
    session:    StreamSession,
    sec_idx:    int,
    start_step: int = 0,
) -> AsyncGenerator[Dict, None]:
    """
    Deliver a full lesson section by iterating through its steps.

    Checks the pause flag between steps.  Does NOT re-emit the section
    heading or title on resume (start_step > 0) because they are already
    visible on the board.

    Delivery order:
      SECTION_START
      For each step from start_step:
        [pause check]
        → _deliver_step
        [BETWEEN_STEP_DELAY_S]
        [pause check]
      SECTION_END  (only if all steps completed without pause)

    PauseContext.segment_heading is populated with section["title"] so that
    the resume bridge can reference which section was in progress.
    """
    sec_type = section.get("type", "UNKNOWN")
    steps    = section.get("steps", [])


    if start_step == 0:
        yield _build_event(
            StreamEventType.SECTION_START,
            {
                "section_index":    sec_idx,
                "section_type":     sec_type,
                "title":            section.get("title", ""),
                "purpose":          section.get("purpose", ""),
                "total_steps":      len(steps),
                "requires_attempt": sec_type in (
                    "GUIDED_PRACTICE",
                    "INDEPENDENT_PRACTICE",
                    "CHALLENGE",
                ),
            },
            sec_idx, sec_type,
        )

    for step_idx in range(start_step, len(steps)):
        if session._pause_flag.is_set():
            session.current_step_index = step_idx
            return
        
        start_group = session.current_group_index if step_idx == start_step else 0

        session.current_step_index = step_idx
        step = steps[step_idx]

        async for ev in _deliver_step(
            step, session, 
            sec_idx, sec_type, 
            step_idx, start_group,
        ):
            yield ev

        if session._pause_flag.is_set():
            # Step was interrupted — either a regular pause_lesson() call,
            # or a raised hand that just got promoted inside _deliver_step
            # (at a group boundary, not necessarily the step boundary).
            # Either way _deliver_step has already left current_group_index
            # pointing at the right resume point; just record which step.
            session.current_step_index = step_idx
            return

        # Breathing room between steps (skip after the last step)
        if step_idx < len(steps) - 1:
            await asyncio.sleep(BETWEEN_STEP_DELAY_S)

    yield _build_event(
        StreamEventType.SECTION_END,
        {"section_index": sec_idx, "section_type": sec_type},
        sec_idx, sec_type,
    )


# ─────────────────────────────────────────────────────────────────────────────
# SESSION MANAGEMENT  (public)
# ─────────────────────────────────────────────────────────────────────────────

def create_session(
    teaching_script: Dict,
    question_bank:   Optional[Dict] = None,
) -> str:
    """
    Create a new streaming session for a lesson delivery.

    Call this after lesson_engine.generate_lesson() returns.
    The `teaching_script` parameter accepts the lesson_engine output dict
    directly — the name "teaching_script" is kept for backward compatibility
    with existing routes.py code.

    Args:
      teaching_script — lesson_engine output (Lesson → Sections → Steps → Events)
      question_bank   — optional pre-warmed bank from answer_engine.anticipate_questions()

    Returns:
      session_id — store in frontend state for all subsequent calls.

    The session starts IDLE.  Call stream_lesson() to begin delivery.
    """
    session_id = str(uuid.uuid4())
    session = StreamSession(
        session_id=session_id,
        teaching_script=teaching_script,
        question_bank=question_bank,
    )
    _save_session(session)
    return session_id


def get_session_state(session_id: str) -> Dict:
    """
    Return a serialisable snapshot of the session's current state.
    Safe to call at any time — does not modify state.

    Returns:
      {
        "session_id":             "uuid",
        "state":                  "IDLE | STREAMING | PAUSED | ...",
        "current_section_index":  int,
        "current_step_index":     int,
        "lesson_title":           "string",
        "total_sections":         int,
        "pause_context":          { ... } | null,
        "created_at":             float,
        "last_active_at":         float
      }
    """
    session = _get_session(session_id)
    lesson  = session.teaching_script

    pause_dict = None
    if session.pause_context:
        pc = session.pause_context
        pause_dict = {
            "segment_index":        pc.segment_index,
            "segment_type":         pc.segment_type,
            "segment_heading":      pc.segment_heading,
            "step_index":           pc.step_index,
            "last_narration":       pc.last_narration,
            "board_state_snapshot": pc.board_state_snapshot,
            "question":             pc.question,
            "pause_reason":         pc.pause_reason.value,
            "paused_at":            pc.paused_at,
            "raised_as_hand":       pc.raised_as_hand,
        }

    return {
        "session_id":            session_id,
        "state":                 session.state.value,
        "current_section_index": session.current_segment_index,
        "current_step_index":    session.current_step_index,
        "lesson_title":          lesson.get("lesson_title", ""),
        "total_sections":        len(lesson.get("sections", [])),
        "pause_context":         pause_dict,
        "created_at":            session.created_at,
        "last_active_at":        session.last_active_at,
        # ── Raised-hand resync ───────────────────────────────────────────
        # Needed on reconnect (e.g. page refresh) to rebuild the frontend's
        # handState without waiting for a live SSE event that may never
        # re-fire:
        #   hand_raised      — true while 'raised'/'acknowledged', i.e. the
        #                      hand is up but not yet promoted into a pause.
        #                      False once promoted (state PAUSED with
        #                      pause_context.raised_as_hand True is the
        #                      signal for the 'active' hand-turn UI at
        #                      that point instead).
        #   hand_ack_emitted — true once HAND_RAISE_ACK has fired for this
        #                      raise, so the frontend can restore
        #                      'acknowledged' rather than 'raised'.
        "hand_raised":           session.hand_raised,
        "hand_ack_emitted":      session.hand_ack_emitted,
    }


# ─────────────────────────────────────────────────────────────────────────────
# LESSON PREFETCH  (internal)
# ─────────────────────────────────────────────────────────────────────────────

async def _prefetch_delivery_plan(session: StreamSession) -> _LessonDeliveryPlan:
    """
    Pre-generate ALL LLM content for the lesson before streaming begins.

    Fires asyncio.gather() over:
      • generate_lesson_opener()                   — 1 LLM call
      • _generate_section_transition() × (N-1)    — N-1 concurrent LLM calls.

    After this runs, stream_lesson() and _deliver_section() are pure event
    iterators — they read from the plan and never await LLM calls themselves.

    Index layout for transitions:
      transitions[0] = ""   (no transition before section 0)
      transitions[i] = transition sentence between section[i-1] and section[i]
    """
    lesson   = session.teaching_script
    sections = lesson.get("sections", [])

    if not sections:
        return _LessonDeliveryPlan(lesson_opener="", segment_transitions=[])

    opener_coro = generate_lesson_opener(lesson)
    transition_coros = [
        _generate_section_transition(
            prev_section=sections[i - 1],
            next_section=sections[i],
            lesson=lesson,
        )
        for i in range(1, len(sections))
    ]

    results     = await asyncio.gather(opener_coro, *transition_coros)
    opener      = results[0]
    transitions = [""] + list(results[1:])

    return _LessonDeliveryPlan(
        lesson_opener=opener,
        segment_transitions=transitions,
    )


# ─────────────────────────────────────────────────────────────────────────────
# CORE STREAMING  (public)
# ─────────────────────────────────────────────────────────────────────────────

async def stream_lesson(session_id: str) -> AsyncGenerator[Dict, None]:
    """
    Primary SSE stream.  Delivers the full lesson from the session's current
    position — either from the beginning (fresh start) or from where a pause
    left off (resume delegates here after the bridge is streamed).

    Reads session.current_segment_index (section index) and
    session.current_step_index to know where to begin.  Both are updated live.

    ── Prefetch phase ─────────────────────────────────────────────────────────
    On FIRST call (delivery_plan is None), builds the full _LessonDeliveryPlan
    before emitting a single SSE event.  On RESUME, the plan is reused.

    ── Delivery order ──────────────────────────────────────────────────────────
    TEACHER_SAYS...  (lesson opener — only on very first call)
    For each section from current_segment_index:
      TEACHER_SAYS  (section transition — from pre-built plan)
      → _deliver_section → _deliver_step → _deliver_concurrent_group → _deliver_single_event
    LESSON_PAUSE     (if interrupted by question or AWAIT_RESPONSE)
    LESSON_COMPLETE  (if all sections delivered)
    """
    session  = _get_session(session_id)
    lesson   = session.teaching_script
    sections = lesson.get("sections", [])

    if not sections:
        yield _build_event(
            StreamEventType.ERROR,
            {"message": "Lesson contains no sections."},
        )
        return

    session.state = LessonStreamState.STREAMING
    _save_session(session)

    # ── Prefetch phase ───────────────────────────────────────────────────────
    is_fresh_start = (
        session.delivery_plan is None
        and session.current_segment_index == 0
        and session.current_step_index == 0
    )

    if session.delivery_plan is None:
        session.delivery_plan = await _prefetch_delivery_plan(session)
        _save_session(session)

    plan      = session.delivery_plan
    start_sec = session.current_segment_index

    # ── Lesson opener — streamed once, before section 0 ─────────────────────
    #    Only on the very first delivery.  The bridge phrase handles re-entry.
    if is_fresh_start and plan.lesson_opener:
        async for ev in _stream_spoken_narration(
            plan.lesson_opener, session, 0, sections[0].get("type", "UNKNOWN"), -1,
            role="opener",
        ):
            yield ev
        await asyncio.sleep(0.5)

    # ── Section delivery loop ────────────────────────────────────────────────
    for sec_idx in range(start_sec, len(sections)):
        section    = sections[sec_idx]
        start_step = session.current_step_index if (sec_idx == start_sec) else 0

        # Between-section transition (pre-computed; no LLM call here)
        transition = (
            plan.segment_transitions[sec_idx]
            if sec_idx < len(plan.segment_transitions)
            else ""
        )
        if transition and start_step == 0:
            # Sleep BEFORE the transition so SECTION_END visually lands
            # and the board clears before the teacher starts speaking again.
            await asyncio.sleep(BETWEEN_SECTION_DELAY_S)
            async for ev in _stream_spoken_narration(
                transition, session, sec_idx, section.get("type", "UNKNOWN"), -1,
                role="transition",
            ):
                yield ev
            await asyncio.sleep(1.2)

        session.current_segment_index = sec_idx
        async for event in _deliver_section(section, session, sec_idx, start_step):
            yield event

        # ── Post-section pause check ─────────────────────────────────────────
        if session._pause_flag.is_set():
            sec       = sections[session.current_segment_index]
            pause_ctx = PauseContext(
                session_id=session_id,
                segment_index=session.current_segment_index,
                segment_type=sec.get("type", "UNKNOWN"),
                segment_heading=sec.get("title", ""),
                step_index=session.current_step_index,
                last_narration=session.last_narration,
                board_state_snapshot=list(session.board_state[-BOARD_SNAPSHOT_DEPTH:]),
                question=session.pending_question,
                pause_reason=session.pending_pause_reason or PauseReason.QUESTION,
                paused_at=time.time(),
                raised_as_hand=session.pending_was_hand_raise,
            )
            session.pending_was_hand_raise = False  # consumed
            session.pause_context = pause_ctx
            session.paused_at     = pause_ctx.paused_at
            session.state         = LessonStreamState.PAUSED
            _save_session(session)

            yield _build_event(
                StreamEventType.LESSON_PAUSE,
                {
                    "session_id":      session_id,
                    "segment_index":   pause_ctx.segment_index,
                    "step_index":      pause_ctx.step_index,
                    "segment_type":    pause_ctx.segment_type,
                    "segment_heading": pause_ctx.segment_heading,
                    "last_narration":  pause_ctx.last_narration,
                    "question":        pause_ctx.question,
                    "pause_reason":    pause_ctx.pause_reason.value,
                    "board_snapshot":  pause_ctx.board_state_snapshot,
                    "raised_as_hand":  pause_ctx.raised_as_hand,
                },
            )
            return

    # ── Lesson complete ───────────────────────────────────────────────────────
    session.state = LessonStreamState.COMPLETE
    _save_session(session)

    yield _build_event(
        StreamEventType.LESSON_COMPLETE,
        {
            "session_id":    session_id,
            "lesson_title":  lesson.get("lesson_title", ""),
            "total_sections": len(sections),
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# TRANSITION GENERATORS  (internal)
# ─────────────────────────────────────────────────────────────────────────────
async def _generate_section_transition(
    prev_section: Dict,
    next_section: Dict,
    lesson:       Dict,
    model:        Optional[str] = None,
) -> str:
    """
    Generate a one-sentence verbal handshake between two lesson sections.
    Called in parallel by _prefetch_delivery_plan() before streaming starts.

    Uses section type and purpose (from lesson_engine) rather than just
    heading so the LLM understands the pedagogical shift, not just the title.
    """
    prompt = (
        f"LESSON: {_build_script_summary(lesson)}\n\n"
        f"FINISHING SECTION: {prev_section.get('type', '?')} — "
        f"\"{prev_section.get('title', '')}\"\n"
        f"(Purpose: {prev_section.get('purpose', 'N/A')})\n\n"
        f"STARTING SECTION:  {next_section.get('type', '?')} — "
        f"\"{next_section.get('title', '')}\"\n"
        f"(Purpose: {next_section.get('purpose', 'N/A')})"
    )
    return await _llm(
        _SECTION_TRANSITION_SYSTEM, prompt,
        model=model, temperature=0.75, max_tokens=120,
    )


async def _generate_hand_ack_bridge(
    session:  StreamSession,
    question: Optional[str],
    model:    Optional[str] = None,
) -> str:
    """
    Generate the short, warm "I see your hand, what's your question?" line
    spoken the moment a raised hand is promoted into a real pause.

    Deliberately NOT the section-transition system: that system is
    prefetched in Phase 1, before streaming starts, with no knowledge of
    runtime events — a hand-raise is inherently a Phase-2 occurrence, so
    it has no transition text pre-computed for it. It's also not the
    resume bridge: that fires on the way OUT of a pause once an answer
    exists; this fires on the way IN, before the question is even known.

    Latency handling: this is NOT called inline at promotion time. It is
    kicked off as a background asyncio task the moment raise_hand() sets
    the soft signal (see raise_hand()), so it typically has the entire
    rest of the current step's delivery time to resolve — by the time
    _deliver_section actually needs the text, the call has usually
    already completed. If it hasn't, the caller applies a short timeout
    and falls back to _HAND_ACK_FALLBACKS rather than stalling the pause.
    """
    known_q = (
        f'They already typed their question: "{question}"\n'
        if question else
        "They haven't typed their question yet — only acknowledge the "
        "raised hand itself, don't reference specific content.\n"
    )
    prompt = (
        f"{_build_script_summary(session.teaching_script)}\n"
        f"What you were just saying: {session.last_narration or '(lesson opening)'}\n"
        f"{known_q}"
        f"{_format_recent_lines(session.recent_hand_acks)}"
        "Write the one-line acknowledgement now."
    )
    try:
        raw = await _llm(
            _HAND_ACK_SYSTEM, prompt,
            model=model, temperature=0.85, max_tokens=60,
        )
        text = raw.strip().strip('"')
        return text or random.choice(_HAND_ACK_FALLBACKS)
    except Exception:
        return random.choice(_HAND_ACK_FALLBACKS)


# How long promotion will wait on the background ack task before giving up
# and using a fallback line. This is a safety net, not the normal path —
# the task has had the entire rest of the step's delivery time to finish.
HAND_ACK_WAIT_TIMEOUT_S: float = 2.5


async def _resolve_hand_ack_text(session: StreamSession) -> str:
    """
    Retrieve the hand-ack line for the raise currently being promoted.

    Prefers the background task started in raise_hand() (should already be
    done by the time this runs). Falls back to a short, varied template if
    the task is missing, still running past HAND_ACK_WAIT_TIMEOUT_S, or
    raised an exception — promotion must never stall indefinitely on an
    LLM call.

    Whichever line is resolved (LLM-generated or fallback) is recorded into
    session.recent_hand_acks so the next raise's prompt can steer away from
    it — this is the single point every path funnels through, so it's the
    right place to record history regardless of how the line was sourced.
    """
    task = session._hand_ack_task
    if task is None:
        line = random.choice(_HAND_ACK_FALLBACKS)
        _remember_line(session.recent_hand_acks, line)
        return line
    try:
        line = await asyncio.wait_for(asyncio.shield(task), timeout=HAND_ACK_WAIT_TIMEOUT_S)
    except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
        line = random.choice(_HAND_ACK_FALLBACKS)
    finally:
        session._hand_ack_task = None
    _remember_line(session.recent_hand_acks, line)
    return line


async def generate_lesson_opener(
    lesson: Dict,
    model:  Optional[str] = None,
) -> str:
    """
    Generate the teacher's opening hook — 2–3 sentences before the first
    board content appears.

    Uses the lesson_engine output dict directly (lesson_title, subject, goal,
    key_concepts, first section type and title).

    Returns plain text string.
    """
    first_section = (lesson.get("sections") or [{}])[0]
    prompt = (
        f"LESSON: {_build_script_summary(lesson)}\n"
        f"FIRST SECTION: {first_section.get('type', '?')} — "
        f"\"{first_section.get('title', '')}\"\n"
        f"KEY CONCEPTS: {', '.join(lesson.get('key_concepts', []))}"
    )
    return await _llm(
        _LESSON_OPENER_SYSTEM, prompt,
        model=model, temperature=0.8, max_tokens=150,
    )


# ─────────────────────────────────────────────────────────────────────────────
# PAUSE  (public)
# ─────────────────────────────────────────────────────────────────────────────

def pause_lesson(
    session_id:   str,
    question:     Optional[str] = None,
    pause_reason: PauseReason   = PauseReason.QUESTION,
) -> Dict:
    """
    Signal the active stream to pause.  Called  when the learner types a
    question mid-lesson (or when the frontend needs a manual pause).

    Sets session._pause_flag.  The active generator checks this flag between
    word-groups (SPEAK) and between steps.  It always completes the current
    atomic unit before stopping — never hangs mid-word.

    Args:
      session_id   — Active session
      question     — Learner's raw question text (stored for bridge context)
      pause_reason — QUESTION (default) | MANUAL | TIMEOUT

    Returns a lightweight acknowledgement.  The full PauseContext is emitted
    as a LESSON_PAUSE SSE event and stored in session.pause_context.

    Frontend flow:
      1.  Receive this return value (confirms flag was set).
      2.  Wait for the LESSON_PAUSE SSE event (confirms delivery stopped).
      3.  Extract pause_context from event payload.
      4.  Pass pause_context to answer_engine.handle_answer_session().
      5.  After CONFIRMED understanding, call resume_lesson().
    """
    session = _get_session(session_id)

    if session.state not in (LessonStreamState.STREAMING, LessonStreamState.RESUMING):
        return {
            "paused":     False,
            "reason":     f"Session is in state {session.state.value}; cannot pause.",
            "session_id": session_id,
        }

    session.pending_question     = question
    session.pending_pause_reason = pause_reason
    session._pause_flag.set()
    _save_session(session)

    return {
        "paused":     True,
        "session_id": session_id,
        "question":   question,
        "note":       "Pause flag set.  Awaiting LESSON_PAUSE event from the stream.",
    }


def raise_hand(
    session_id: str,
    question:   Optional[str] = None,
) -> Dict:
    """
    Signal a "raised hand" — a soft attention request.  Called when the
    learner wants to ask something but the frontend UX is "raise hand"
    rather than "interrupt now" (e.g. tapping a hand icon while the
    teacher is mid-explanation).

    Unlike pause_lesson(), this does NOT set session._pause_flag, so
    delivery is NOT cut at the next word/group boundary.  Instead it sets
    session._hand_flag, which is honoured at the very next GROUP boundary
    — i.e. as soon as whatever sentence/board-action is already in flight
    finishes, not the rest of the step. At that boundary:
      • a HAND_RAISE_ACK event fires (frontend can show a "noted" indicator)
      • the teacher then SPEAKS a short, warm acknowledgement line ("Hold
        that thought — I see your hand, what's your question?"-style,
        never a robotic form-fill line — see _HAND_ACK_SYSTEM)
      • a LESSON_PAUSE event follows with raised_as_hand: true in its
        payload — same downstream flow as pause_lesson() from there.

    This mirrors a real classroom: the teacher sees the hand, finishes the
    sentence she's mid-way through, then turns to the learner — she
    doesn't freeze mid-word, but she also doesn't keep going through
    several more unrelated sentences first.

    If the learner puts their hand down before the promotion happens, call
    lower_hand(session_id) to cancel it silently (no pause will occur).

    Args:
      session_id — Active session
      question   — Learner's question text, if already typed/spoken at
                   raise-time.  Optional — the frontend may raise the hand
                   first and collect the question only once the teacher
                   actually turns to them (i.e. after LESSON_PAUSE lands),
                   in which case pass it later via pause_lesson() instead,
                   or call raise_hand() again to update the stored text
                   before the promotion fires.

    Returns a lightweight acknowledgement.  A HAND_RAISE_ACK SSE event
    will also arrive shortly after via the active stream once the current
    group boundary is reached; use whichever the frontend needs.
    """
    session = _get_session(session_id)

    if session.state not in (LessonStreamState.STREAMING, LessonStreamState.RESUMING):
        return {
            "acknowledged": False,
            "reason":       f"Session is in state {session.state.value}; cannot raise hand.",
            "session_id":   session_id,
        }

    session.hand_raised         = True
    session.hand_raise_question = question
    session.hand_ack_emitted    = False   # allow a fresh HAND_RAISE_ACK for this raise

    # Cancel any stale ack task from a previous raise (e.g. learner raised,
    # lowered, and raised again) before starting a fresh one.
    if session._hand_ack_task is not None and not session._hand_ack_task.done():
        session._hand_ack_task.cancel()

    # Kick off the "I see your hand, what's your question?" line NOW, in
    # the background, while the teacher keeps talking. By the time the
    # current step finishes and the raise gets promoted into a real pause,
    # this has almost always already resolved — see
    # _generate_hand_ack_bridge()'s docstring for why this isn't generated
    # inline at promotion time.
    try:
        session._hand_ack_task = asyncio.create_task(
            _generate_hand_ack_bridge(session, question)
        )
    except RuntimeError:
        # No running event loop (e.g. called from sync test code) — the
        # promotion step falls back to _HAND_ACK_FALLBACKS in this case.
        session._hand_ack_task = None

    session._hand_flag.set()
    _save_session(session)

    return {
        "acknowledged": True,
        "session_id":   session_id,
        "question":     question,
        "note":         "Hand noted.  Teacher will finish this step, then pause.",
    }


def lower_hand(session_id: str) -> Dict:
    """
    Cancel a previously raised hand before it gets promoted into a real
    pause — e.g. the learner tapped the hand icon by accident, or figured
    out the answer themselves before the teacher got to them.

    No-op (but safe) if the hand was already promoted into a pause or was
    never raised.
    """
    session = _get_session(session_id)

    was_pending = session._hand_flag.is_set() and not session._pause_flag.is_set()

    if session._hand_ack_task is not None and not session._hand_ack_task.done():
        session._hand_ack_task.cancel()
    session._hand_ack_task      = None

    session.hand_raised         = False
    session.hand_raise_question = None
    session.hand_ack_emitted    = False
    session._hand_flag.clear()
    _save_session(session)

    return {
        "lowered":    True,
        "session_id": session_id,
        "was_pending": was_pending,
    }


# ─────────────────────────────────────────────────────────────────────────────
# RESUME  (public)
# ─────────────────────────────────────────────────────────────────────────────

def _find_next_content(
        session: StreamSession, 
        step_offset: int = 0,
        prefer_write: bool = False,
        write_only:   bool = False,
        last_write:   bool = False, 
    ) -> str:
    """
    Look ahead at the next SPEAK or WRITE event that will appear once the
    lesson resumes, starting step_offset steps past session.current_segment_index
    / current_step_index.

    step_offset=1 is for AWAIT_RESPONSE pauses where the caller has NOT
    already advanced session.current_step_index past the paused step (e.g.
    generate_resume_bridge(), which is read-only and must not mutate
    session state). resume_lesson() DOES advance current_step_index for
    real before calling this, so it uses the default step_offset=0.

    This distinction matters: the paused step's own WRITE event is the
    *problem* ("6y + 4y - 3"), not the answer. The answer only appears in
    the following step, which lesson_engine scripts unconditionally.
    """
    sections = session.teaching_script.get("sections", [])
    next_sec_idx  = session.current_segment_index
    next_step_idx = session.current_step_index + step_offset

    def _first_from_events(events: list) -> str:
        if last_write:
            # Scan all events, keep updating on each WRITE found
            # so the final WRITE (completed answer) is returned.
            # Falls back to first SPEAK if no WRITE exists at all.
            last = None
            for ev in events:
                if ev.get("type") == "WRITE" and ev.get("content"):
                    last = ev["content"]
            if last:
                return last
            for ev in events:
                if ev.get("type") == "SPEAK" and ev.get("content"):
                    return ev["content"]
            return ""
        
        if write_only:
            for ev in events:
                if ev.get("type") == "WRITE" and ev.get("content"):
                    return ev["content"]
            return ""

        if prefer_write:
            for ev in events:
                if ev.get("type") == "WRITE" and ev.get("content"):
                    return ev["content"]
            # No WRITE found — fall through to SPEAK/WRITE fallback scan
        for ev in events:
            if ev.get("type") in ("WRITE", "SPEAK") and ev.get("content"):
                return ev["content"]
        return ""
    

    if next_sec_idx < len(sections):
        sec   = sections[next_sec_idx]
        steps = sec.get("steps", [])
        if next_step_idx < len(steps):
            result = _first_from_events(steps[next_step_idx].get("events", []))
            if result:
                return result
            
        elif next_sec_idx + 1 < len(sections):
            nxt_steps = sections[next_sec_idx + 1].get("steps", [])
            if nxt_steps:
                result = _first_from_events(nxt_steps[0].get("events", []))
                if result:
                    return result

    return "(next content unavailable)"


async def _grade_practice_attempt(
    question:         str,
    expected_content: str,
    attempt:          str,
    model:            Optional[str] = None,
) -> Dict:
    """
    Silent grading pass for an AWAIT_RESPONSE practice attempt — separate
    from bridge generation so the creative, warm bridge-writing call can be
    handed a clean verdict instead of having to grade AND write naturally
    in the same pass.

    Returns {"correct": bool | None, "reason": str}.  "correct" is None
    when there's nothing to grade (blank attempt) or the grading call
    itself failed — grading is a nice-to-have, not a gate, so failures
    fall back to an ungraded acknowledgement rather than blocking resume.
    """
    if not attempt.strip():
        return {"correct": None, "reason": "No attempt was submitted."}

    prompt = (
        f"Problem posed to the learner:\n{question}\n\n"
        f"Correct answer / what the lesson reveals next:\n{expected_content}\n\n"
        f"Learner's submitted attempt:\n{attempt}\n\n"
        "Return the JSON verdict now."
    )
    try:
        raw     = await _llm(
            _PRACTICE_GRADER_SYSTEM,
            prompt,
            model=model,
            temperature=0.0,
            max_tokens=80,
        )
        verdict = json.loads(_strip_json(raw))
        return {
            "correct": bool(verdict.get("correct")),
            "reason":  str(verdict.get("reason", ""))[:200],
        }
    except Exception:
        return {"correct": None, "reason": ""}


def _build_resume_bridge_prompt(
    session:        StreamSession,
    answer_summary: Dict,
    grading:        Optional[Dict] = None,
    next_content:   Optional[str]  = None,
) -> str:
    """
    Build the LLM prompt for the resume bridge.

    Shared by generate_resume_bridge() and resume_lesson().

    Looks ahead at the next SPEAK or WRITE event coming up so the bridge
    can naturally set up what the teacher is about to do next.  For
    AWAIT_RESPONSE pauses, uses language about the learner's attempt rather
    than a Q&A digression.

    Args:
      grading      — Pre-computed verdict from _grade_practice_attempt(),
                      or None.  Only meaningful for AWAIT_RESPONSE pauses;
                      ignored otherwise.
      next_content — Pre-computed lookahead (see _find_next_content()).  If
                      omitted, falls back to _find_next_content(session)
                      with no offset.
    """
    pause_ctx = session.pause_context
    lesson    = session.teaching_script

    if next_content is None:
        next_content = _find_next_content(session, prefer_write=True)

    pause_ctx_text = (
        _format_pause_context_for_prompt(pause_ctx)
        if pause_ctx
        else "(no pause context)"
    )

    # For AWAIT_RESPONSE, describe it as a graded practice pause, not a Q&A.
    is_await = (
        pause_ctx and pause_ctx.pause_reason == PauseReason.AWAIT_RESPONSE
    )
    thin_context = False
    if is_await:
        attempt_text = (
            answer_summary.get("raw_attempt")
            or answer_summary.get("core_explanation")
            or "(no attempt text captured)"
        )
        if grading is None or grading.get("correct") is None:
            verdict_line = "Verdict         : UNGRADED — acknowledge the attempt warmly without claiming it's right or wrong."
        elif grading["correct"]:
            verdict_line = f"Verdict         : CORRECT ({grading.get('reason', '')})"
        else:
            verdict_line = f"Verdict         : INCORRECT ({grading.get('reason', '')})"
        answer_text = (
            f"Pause type      : PRACTICE ATTEMPT (learner tried the problem)\n"
            f"Problem posed   : {pause_ctx.question or '(see board)'}\n"
            f"Learner answered: {attempt_text}\n"
            f"{verdict_line}\n"
        )
    else:
        core_explanation = answer_summary.get("core_explanation")
        thin_context = not core_explanation or core_explanation in (
            "(not provided)",
            "Student confirmed understanding.",
        )
        answer_text = (
            f"Question type   : {answer_summary.get('question_type', 'GENERAL')}\n"
            f"Approach used   : {answer_summary.get('approach_used', 'ALGEBRAIC')}\n"
            f"Core insight    : {core_explanation or '(not provided)'}\n"
            f"Question asked  : {answer_summary.get('question', pause_ctx.question if pause_ctx else '')}"
        )

    thin_context_note = (
        "\nNOTE: Core insight is missing or generic for this turn — do NOT\n"
        "invent specifics about what was explained, and do NOT mention that\n"
        "the detail is missing. Bridge using WHERE WE PAUSED and WHAT COMES\n"
        "NEXT ON THE BOARD alone: acknowledge that the question is resolved\n"
        "in one warm, general phrase, then lead straight into what's next.\n"
        if thin_context else ""
    )

    board_line = (
        f"WHAT COMES NEXT ON THE BOARD:\n{next_content}\n\n"
        if next_content
        else
        "WHAT COMES NEXT ON THE BOARD:\n(no board write — teacher speaks to confirm)\n\n"
    )

    return (
        f"LESSON CONTEXT:\n{_build_script_summary(lesson)}\n\n"
        f"WHERE WE PAUSED:\n{pause_ctx_text}\n\n"
        f"WHAT WAS DISCUSSED:\n{answer_text}\n"
        f"{thin_context_note}\n"
        + board_line
        + _format_recent_lines(session.recent_bridges)
        + "Write the teacher's re-entry bridge.  1–3 sentences.  Plain text only."
    )


async def generate_resume_bridge(
    session:        StreamSession,
    answer_summary: Dict,
    model:          Optional[str] = None,
) -> str:
    """
    Generate the natural teacher re-entry phrase after a Q&A digression
    or a practice attempt pause.

    This is the most important function in the engine for the "alive" feel.
    It reads the full pause context and produces a warm, specific bridge —
    never a template, never mechanical.

    Args:
      session        — Active StreamSession (contains pause_context)
      answer_summary — Dict with answer_engine data:
                        {
                          "question":        "...",
                          "approach_used":   "ANALOGY | NUMERICAL | ...",
                          "question_type":   "WHY | HOW | ...",
                          "core_explanation": "one-line summary"
                        }
                       For AWAIT_RESPONSE pauses, "core_explanation" instead
                       carries the learner's raw attempt text, which gets
                       graded against the lesson's own scripted answer
                       before the bridge is written. Pass {} if not
                       applicable.

    Read-only: unlike resume_lesson() (the actual delivery path), this does
    not record its output into session.recent_bridges — it may be called
    speculatively for a preview without the bridge actually being spoken.

    Returns plain text string (1–3 sentences).
    """
    pause_ctx = session.pause_context
    is_await  = bool(pause_ctx and pause_ctx.pause_reason == PauseReason.AWAIT_RESPONSE)

    # Read-only preview: this function does not advance
    # session.current_step_index the way resume_lesson() does, so look one
    # extra step ahead for AWAIT_RESPONSE (see _find_next_content's docstring).
    next_content = _find_next_content(
        session,
        step_offset=1 if is_await else 0,
        write_only=True,            # board field must only ever contain WRITE content
    )

    grading = None
    if is_await:
        grading = await _grade_practice_attempt(
            question=pause_ctx.question or "",
            expected_content=next_content,
            attempt=answer_summary.get("core_explanation", ""),
            model=model,
        )

    prompt = _build_resume_bridge_prompt(session, answer_summary, grading, next_content)
    bridge = await _llm(
        _RESUME_BRIDGE_SYSTEM,
        prompt,
        model=model,
        temperature=0.80,
        max_tokens=160,
    )
    return bridge.strip()


async def resume_lesson(
    session_id:     str,
    answer_summary: Dict,
    model:          Optional[str] = None,
) -> AsyncGenerator[Dict, None]:
    """
    Resume an interrupted lesson after the learner has confirmed understanding
    (or completed an attempt for an AWAIT_RESPONSE pause).

    The frontend opens this stream after answer_engine returns resume_lesson=True
    (or after the learner's attempt is acknowledged).

    Delivery order:
      RESUME_BRIDGE { "phase": "begin" }
      TEACHER_SAYS... (bridge phrase, streamed at speaking pace)
      RESUME_BRIDGE { "phase": "end" }
      [brief beat]
      → delegates back to stream_lesson()

    The bridge is resolved to a complete string FIRST (via _llm()), then paced
    through _stream_text_chunks() so it reads at the same speed as all other
    narration.  (Raw token streaming would blast it out at network speed.)

    Args:
      session_id     — The paused session
      answer_summary — See generate_resume_bridge(); pass {} for AWAIT_RESPONSE.
    """
    session = _get_session(session_id)

    if session.state != LessonStreamState.PAUSED:
        yield _build_event(
            StreamEventType.ERROR,
            {
                "code":    "ALREADY_RESUMED",
                "message": f"Session {session_id} is not paused (state: {session.state.value}).",
            },
        )
        return

    pause_ctx = session.pause_context
    is_await  = bool(pause_ctx and pause_ctx.pause_reason == PauseReason.AWAIT_RESPONSE)

    session.state = LessonStreamState.RESUMING

    if is_await:
        session.current_step_index += 1
        session.current_group_index = 0# new step, start from 1st group

    _save_session(session)

    # Meta fields for TEACHER_SAYS events during the bridge
    sections = session.teaching_script.get("sections", [])
    sec_idx  = session.current_segment_index
    sec_type = (
        sections[sec_idx].get("type", "UNKNOWN")
        if sec_idx < len(sections)
        else "UNKNOWN"
    )
    step_idx = session.current_step_index

    # ── 1. Grade the attempt, then resolve the bridge text ────────────────────
    next_content = _find_next_content(session, last_write=True)
    grading = None
    # In resume_lesson(), change the grading call to:
    if is_await:
        raw_attempt = answer_summary.get("raw_attempt", "").strip()
        if raw_attempt:
            grading = await _grade_practice_attempt(
                question=pause_ctx.question or "",
                expected_content=next_content,
                attempt=raw_attempt,
            )
        else:
            # No raw math attempt — learner went through Q&A instead.
            # Fall back to UNGRADED so bridge opens neutrally.
            grading = {"correct": None, "reason": "No direct attempt submitted."}

    prompt      = _build_resume_bridge_prompt(session, answer_summary, grading, next_content)
    bridge_text = await _llm(
        _RESUME_BRIDGE_SYSTEM,
        prompt,
        model=model,
        temperature=0.80,
        max_tokens=160,
    )
    _remember_line(session.recent_bridges, bridge_text.strip())

    # ── 2. Signal bridge start ────────────────────────────────────────────────
    yield _build_event(StreamEventType.RESUME_BRIDGE, {"phase": "begin"})

    session._pause_flag.clear()

    # Beat before speaking — see RESUME_BRIDGE_BREATH_S. Without this the
    # bridge launches in the same instant as "begin", which feels like a
    # fresh process picking up cold rather than the same teacher naturally
    # re-engaging after the digression.
    await asyncio.sleep(RESUME_BRIDGE_BREATH_S)

    # ── 3. Stream bridge at natural`` speaking pace ─────────────────────────────
    async for ev in _stream_spoken_narration(
        bridge_text.strip(), session, sec_idx, sec_type, step_idx, role="bridge"
    ):
        yield ev

    # A learner interrupted the bridge itself — stop here instead of
    # continuing on to "resume normal streaming." Overwriting their new
    # pause_context/pending_question by falling through to step 5 would
    # silently drop the interruption they just asked for.
    if session._pause_flag.is_set():
        return

    # ── 4. Signal bridge end + breath before lesson resumes ──────────────────
    yield _build_event(StreamEventType.RESUME_BRIDGE, {"phase": "end"})
    await asyncio.sleep(0.6)

    # ── 5. Clear pause state and delegate back to stream_lesson ──────────────
    session._pause_flag.clear()
    session.pending_question     = None
    session.pending_pause_reason = None
    session.state                = LessonStreamState.STREAMING
    _save_session(session)

    async for event in stream_lesson(session_id):
        yield event


# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES  (public — called from routes.py or directly by tests)
# ─────────────────────────────────────────────────────────────────────────────

def store_answer_envelope(session_id: str, envelope: Dict) -> None:
    """
    Store an answer_engine envelope in the session for deferred SSE delivery.
    Called by routes.py immediately after handle_answer_session() returns an
    ANSWER / ESCALATE / PROBE / MICRO envelope.  The frontend then opens
    GET /stream/answer to receive it as a paced SSE stream.
    """
    session = _get_session(session_id)
    session.pending_answer_envelope = envelope
    _save_session(session)


async def stream_answer_envelope(session_id: str) -> AsyncGenerator[Dict, None]:
    """
    Stream a stored answer_engine envelope through the same delivery machinery
    that lesson_engine sections use.

    The envelope's sections are fed through _deliver_section() so every
    SPEAK event arrives word-by-word at NARRATION_CHUNK_DELAY_S pace, every
    WRITE event arrives character-by-character at SYNC_BOARD_WRITE_DELAY_S
    pace, and sync_with_previous=true events are interleaved concurrently —
    identical behaviour to a live lesson section.

    IMPORTANT — lesson resume-pointer preservation:
      _deliver_section() mutates session.current_step_index as it tracks
      its position.  That field is the lesson's resume pointer — stream_lesson()
      uses it to know where to restart after a pause.  We save and restore it
      so that when the learner confirms understanding and /stream/resume fires,
      the lesson picks up from exactly where it paused, not from some step
      inside the answer section.

      session.last_narration and session.board_state are NOT restored — they
      should reflect what was actually displayed to the learner most recently,
      which is the answer content.

    Yields:
      Same event types as stream_lesson() — SECTION_START, STEP_START,
      TEACHER_SAYS, BOARD_WRITE_*, annotation events, LEARNER_CHECKPOINT,
      STEP_END, SECTION_END — then a final ANSWER_COMPLETE event.

    Emits ERROR if no envelope is stored or the session does not exist.
    """
    session = _get_session(session_id)
    envelope = session.pending_answer_envelope

    if not envelope:
        yield _build_event(
            StreamEventType.ERROR,
            {"message": "No answer envelope is pending for this session."},
        )
        return

    sections = envelope.get("sections", [])
    if not sections:
        yield _build_event(
            StreamEventType.ERROR,
            {"message": "Answer envelope contains no sections."},
        )
        return

    # Save lesson resume pointers (see docstring above)
    saved_segment_index = session.current_segment_index
    saved_step_index    = session.current_step_index
    saved_group_index   = session.current_group_index
    session.current_group_index = 0

    # Clear the pause flag so the answer envelope can stream. 
    # (left True by the main lesson pause).
    session._pause_flag.clear()


    interrupted = False
    try:
        for sec_idx, section in enumerate(sections):
            async for event in _deliver_section(
                section=section,
                session=session,
                sec_idx=sec_idx,
                start_step=0,
            ):
                yield event

            if session._pause_flag.is_set():
                interrupted = True   # ← track it
                break

    finally:
        session.current_segment_index = saved_segment_index
        session.current_step_index    = saved_step_index
        session.current_group_index   = saved_group_index
        session.pending_answer_envelope = None
        _save_session(session)

    if not interrupted:             # ← only emit if we finished cleanly
        yield _build_event(
            StreamEventType.ANSWER_COMPLETE,
            {
                "session_id": session_id,
                "question":   envelope.get("question", ""),
            },
        )


def list_sessions() -> List[Dict]:
    """
    Return a lightweight summary of all in-memory sessions.
    Useful for admin endpoints and health checks.
    """
    return [
        {
            "session_id":    sid,
            "state":         s.state.value,
            "lesson":        s.teaching_script.get("lesson_title", ""),
            "section":       s.current_segment_index,
            "step":          s.current_step_index,
            "last_active":   s.last_active_at,
        }
        for sid, s in _SESSIONS.items()
    ]


def evict_session(session_id: str) -> bool:
    """Remove a session from memory.  Returns True if it existed."""
    return bool(_SESSIONS.pop(session_id, None))


def evict_stale_sessions(max_age_seconds: float = 7200.0) -> int:
    """
    Remove sessions idle longer than max_age_seconds.
    Call periodically from a background task in main.py.
    Returns the number of sessions removed.
    """
    now   = time.time()
    stale = [
        sid for sid, s in _SESSIONS.items()
        if now - s.last_active_at > max_age_seconds
    ]
    for sid in stale:
        _SESSIONS.pop(sid, None)
    return len(stale)