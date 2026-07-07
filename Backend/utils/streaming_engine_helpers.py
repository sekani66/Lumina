import re

def _strip_json(raw: str) -> str:
    """Strip markdown fences that LLMs sometimes wrap around JSON."""
    return re.sub(r"```(?:json)?", "", raw).strip()

