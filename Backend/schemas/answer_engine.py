# ════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS — Answer engine (answer_engine.py)
# ════════════════════════════════════════════════════════════════════════════

from typing import Dict, Optional, List
from pydantic import BaseModel


class AnticipateRequest(BaseModel):
    """
    POST /answer/anticipate
    Pre-scans a teaching script and generates a full question bank.
    Call once after /lesson/generate; pass the bank to /stream/session/create.
    """
    teaching_script: Dict
    model:           Optional[str] = None


class AnswerSessionRequest(BaseModel):
    """
    POST /answer/ask  — primary Q&A endpoint.

    Turn 1 (initial question):
      Pass question, active_segment, teaching_script, session_id.
      Leave learner_response = None.

    Turn 2+ (learner replied):
      Also pass learner_response, examples_given, previous_approach,
      approaches_used, probe_question, seconds_since_prompt, and
      timeout_grace_used from the previous response envelope.

    After probe (confusion located):
      Also pass confusion_location = learner's answer to the probe question.

    session_id is used to look up the per-session background anticipation
    task fired by /stream/session/create — no explicit question_bank needed.
    """
    question:             str
    active_segment:       Dict
    teaching_script:      Dict
    session_id:           Optional[str]   = None   # for bg-task bank lookup
    learner_response:     Optional[str]   = None
    conversation_history: List[Dict]      = []
    examples_given:       int             = 0
    previous_approach:    Optional[str]   = None
    approaches_used:      List[str]       = []
    question_bank:        Optional[Dict]  = None   # explicit override; usually unneeded
    confusion_location:   Optional[str]   = None
    probe_question:       Optional[str]   = None   # literal AWAIT_RESPONSE text from prior turn
    seconds_since_prompt: Optional[float] = None   # wall-clock s since last probe was issued
    timeout_grace_used:   bool            = False  # whether one silent-timeout grace was given
    awaiting_final_confirmation: bool     = False  # true when the previous turn's payload WAS
                                                    # the soft "does that make sense" check — pass
                                                    # straight back so the reply is graded as a
                                                    # real confirmation instead of another probe
    board_state:          List[str]       = []     # running board state for this Q&A thread
    core_explanation:      Optional[str]  = None    # one-line summary of the last substantive
                                                      # explanation given this thread (from the
                                                      # previous response's core_explanation) —
                                                      # feeds the resume bridge so it isn't
                                                      # contextless; see handle_answer_session
    model:                Optional[str]   = None


class ClassifyUnderstandingRequest(BaseModel):
    """
    POST /answer/understand
    Classifies a learner's reply as CONFIRMED / UNCERTAIN / NOT_CONFIRMED.
    question is required — the classifier needs it to judge the reply in context.
    examples_given is forwarded so the engine can auto-escalate at MAX_EXAMPLES.
    probe_question, when supplied, lets the agent grade a direct answer attempt
    (CORRECT / PARTIAL / INCORRECT) rather than just reading general comprehension.
    active_segment and conversation_history are accepted for completeness but are
    not currently forwarded to classify_understanding() (the engine uses keyword
    scan + lightweight LLM; full segment context is not needed there).
    """
    learner_response:     str
    question:             str                   # required by classify_understanding()
    examples_given:       int            = 1    # triggers ESCALATED threshold if >= MAX
    probe_question:       Optional[str]  = None # literal AWAIT_RESPONSE text for probe grading
    active_segment:       Dict           = {}   # kept for context; not forwarded to engine
    conversation_history: List[Dict]     = []   # kept for context; not forwarded to engine
    model:                Optional[str]  = None


class EscalateRequest(BaseModel):
    """
    POST /answer/escalate
    Generates a re-explanation using a completely different teaching approach.
    ALGEBRAIC → ANALOGY → NUMERICAL → CONTRAST → BACKWARDS → STORY → VISUAL

    conversation_history and example_number are required by escalate_with_example().
    approaches_used is tracked client-side for UI state; it is not forwarded to
    the engine (the engine derives the next approach from example_number alone).
    """
    question:             str
    active_segment:       Dict
    teaching_script:      Dict
    previous_approach:    Optional[str] = None
    approaches_used:      List[str]     = []    # tracked client-side; not forwarded
    conversation_history: List[Dict]    = []
    example_number:       int           = 1     # 1-based escalation count
    model:                Optional[str] = None


class ProbeRequest(BaseModel):
    """
    POST /answer/probe  — two-turn confusion-location flow.

    Turn 1 (confusion_location = None):
      Calls probe_confusion_point() → returns a probe_question for the learner.

    Turn 2 (confusion_location = learner's answer to the probe question):
      Calls generate_micro_explanation() → returns a surgical 2–4 sentence fix.

    examples_given is forwarded to probe_confusion_point() so it can log how
    many escalation attempts preceded the probe.
    """
    question:           str
    active_segment:     Dict
    teaching_script:    Dict
    confusion_location: Optional[str] = None
    examples_given:     int           = 3    # escalation count at probe time
    model:              Optional[str]  = None

