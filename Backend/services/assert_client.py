from fastapi import HTTPException
from pipelines import llm_gateway as gateway

def _assert_client() -> None:
    """Raise HTTP 503 when no configured LLM provider is ready to serve requests."""
    if not gateway.is_ready():
        raise HTTPException(status_code=503, detail="No LLM provider is configured.")

