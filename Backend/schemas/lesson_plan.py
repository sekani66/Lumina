# ════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS — Lesson planning (lesson_engine.py)
# ════════════════════════════════════════════════════════════════════════════

from typing import List, Optional, Dict
from pydantic import BaseModel


class LessonGenerateRequest(BaseModel):
    """
    POST /lesson/generate
    Converts a single lesson stub from the course plan into a fully planned,
    board-ready lesson — sections, steps, and presentation events.
    """
    lesson_id:             str
    lesson_title:          str
    key_concepts:          List[str]            = []
    prerequisite_revision: str                  = ""
    description:           str                  = ""
    subject:               str                  = "General"
    grade_level:           str                  = "Not specified"
    goal:                  str                  = "Deep Mastery"
    weak_prerequisites:    Optional[List[str]]  = None
    source_context:        Optional[str]        = None
    model:                 Optional[str]        = None


class LessonSegmentExplainRequest(BaseModel):
    """
    POST /lesson/segment/explain
    Returns a deeper prose explanation for one segment.
    segment should be the full segment dict from a /lesson/generate response.
    """
    segment:      Dict
    lesson_title: str
    subject:      str           = "General"
    model:        Optional[str] = None

