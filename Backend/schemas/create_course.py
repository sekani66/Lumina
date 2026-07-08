# ════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS — Course creation
# ════════════════════════════════════════════════════════════════════════════

from typing import Optional, Dict
from pydantic import BaseModel, field_validator

VALID_RATINGS = frozenset({1, 2, 3, 4})
RATING_LABELS: Dict[int, str] = {
    1: "Novice",
    2: "Familiar",
    3: "Confident",
    4: "Master",
}


class PrerequisiteRequest(BaseModel):
    topic:          str
    goal:           str
    source_summary: Optional[str] = None   # populated from /extract-pdf response
    model:          Optional[str] = None


class CourseRequest(BaseModel):
    topic:          str
    goal:           str
    no_source:      bool             = True
    # keys  = prerequisite id strings (as returned by /prerequisites)
    # values = rating integers 1–4
    prerequisites:  Dict[str, int]   = {}
    source_summary: Optional[str]    = None   # populated from /extract-pdf response
    model:          str = 'reasoning'

    @field_validator("prerequisites")
    @classmethod
    def validate_ratings(cls, v: Dict[str, int]) -> Dict[str, int]:
        for key, rating in v.items():
            if rating not in VALID_RATINGS:
                raise ValueError(
                    f"Rating for '{key}' must be 1–4 (got {rating})."
                )
        return v

