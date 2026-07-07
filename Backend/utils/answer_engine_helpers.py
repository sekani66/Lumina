import re
from typing import Optional, Dict, List


def _strip_fences(raw: str) -> str:
    """Strip markdown fences that LLMs sometimes wrap around JSON output."""
    m = re.match(r"^```(?:json)?\s*\n?(.*?)```$", raw, re.DOTALL)
    if m:
        return m.group(1).strip()
    return raw.strip()


def _is_blank(response: Optional[str]) -> bool:
    """
    True if the learner has not actually said anything yet — empty string,
    None, or punctuation/whitespace only. This is NOT a confirmation-phrase
    check; it only detects "no reply", which the timeout policy needs in
    order to start its clock. Every non-blank reply still goes to the LLM.
    """
    if not response:
        return True
    return bool(re.fullmatch(r"[.?!…\s]*", response))


# ─── Answer-engine response shaping ──────────────────────────────────────────
# answer_engine returns SPEAK/WRITE/PAUSE/AWAIT_RESPONSE event envelopes
# for every action — the same format lesson sections use — so streaming_engine
# can play an answer exactly like lesson content with no special-cased path.
#
# For the /answer/ask primary endpoint the payload is already the right shape
# (handle_answer_session puts the envelope directly in result["payload"]).
# The three helpers below are used only by the three STANDALONE endpoints
# (/answer/escalate, /answer/probe) to surface the envelope alongside
# useful metadata in a consistent action-response wrapper.

def _flatten_escalation(escalate_result: Dict, approaches_used: Optional[List[str]] = None) -> Dict:
    """
    Wrap escalate_with_example()'s output for the standalone /answer/escalate
    endpoint. The engine now returns an event-stream envelope (type/question/
    resume/sections) rather than a flat explanation dict — pass it through
    directly alongside the key session-management metadata.
    """
    return {
        "action":               "ESCALATE",
        "payload":              escalate_result.get("envelope", {}),
        "approach_used":        escalate_result.get("approach_used", ""),
        "examples_given":       escalate_result.get("examples_given", 0),
        "probe_question":       escalate_result.get("probe_question"),
        "understanding_status": escalate_result.get("understanding_status", "PENDING"),
        "approaches_used":      approaches_used if approaches_used is not None else [],
    }


def _flatten_probe(probe_result: Dict) -> Dict:
    """
    Wrap probe_confusion_point()'s output for Turn 1 of the standalone
    /answer/probe endpoint. Returns the event-stream envelope alongside
    probe_question (the exact AWAIT_RESPONSE text the frontend forwards back
    as confusion_location on Turn 2) and what_answer_reveals diagnostic hints.
    """
    return {
        "action":               "PROBE",
        "payload":              probe_result.get("envelope", {}),
        "probe_question":       probe_result.get("probe_question"),
        "what_answer_reveals":  probe_result.get("what_answer_reveals", {}),
        "examples_given":       probe_result.get("examples_given", 0),
        "understanding_status": probe_result.get("understanding_status", "ESCALATED"),
    }


def _flatten_micro(micro_result: Dict) -> Dict:
    """
    Wrap generate_micro_explanation()'s output for Turn 2 of the standalone
    /answer/probe endpoint. Returns the event-stream envelope alongside
    confusion_at (where the learner said they got lost) and probe_question
    (the confirming AWAIT_RESPONSE in the micro-explanation).
    """
    return {
        "action":               "MICRO",
        "payload":              micro_result.get("envelope", {}),
        "confusion_location":   micro_result.get("confusion_at", ""),
        "probe_question":       micro_result.get("probe_question"),
        "understanding_status": micro_result.get("understanding_status", "PENDING"),
    }

