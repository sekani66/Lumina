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
    model:                 Optional[str]        = 'reasoning'



