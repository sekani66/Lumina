"""
Lumina LLM Gateway
═══════════════════════════════════════════════════════════════════════════
PURPOSE
  The single seam between every engine file (extractor.py, lesson_engine.py,
  answer_engine.py, streaming_engine.py, routes.py) and whatever model
  provider is actually running underneath (OpenAI, or Fireworks-hosted
  models). No engine file  import the openai SDK or build a client
  directly — they all just call:

      from agents import llm_gateway as gateway

      text = await gateway.complete("Explain the chain rule.")
      data = await gateway.complete_json([...messages...], system="...")

  Swapping the model behind the whole app is one-line env var change
  (see CONFIGURATION below) — no engine file needs to change.

═══════════════════════════════════════════════════════════════════════════
WHY TWO LAYERS OF ROUTING

  1. ALIASES   — logical task-tier names ("fast" / "default" / "reasoning")
                 that callers should request instead of hardcoding a vendor
                 model id. This is what actually makes the swap painless:
                 flipping LLM_DEFAULT_MODEL from "Fire works" to a
                 AMD-hosted model id moves every call site that used
                 "default" at once, with zero code edits.

  2. PREFIXES  — concrete model id → which SDK/provider serves it. Needed
                 because OpenAI and Fireworks model ids look different even
                 though the gateway exposes one interface. This layer exists
                 so a caller can still pass a literal model string
                 (back-compat with existing
                 `model: Optional[str] = "gpt-4o-mini"` fields) and have it
                 routed correctly without going through an alias at all.

═══════════════════════════════════════════════════════════════════════════
CONFIGURATION (.env)

  OPENAI_API_KEY=sk-...

  FIREWORKS_API_KEY=fw_...                    # Fireworks-hosted models
  FIREWORKS_BASE_URL=https://api.fireworks.ai/inference/v1   # default; only
                                               # allows override for a dedicated
                                               # deployment or account alias

  VLLM_BASE_URL=http://<host>:8000/v1         # self-hosted vLLM instance
                                               # (e.g. the AMD-GPU notebook
                                               # running `vllm serve Qwen/Qwen3-14B`)
  VLLM_API_KEY=EMPTY                          # vLLM doesn't check this by
                                               # default; the OpenAI SDK just
                                               # requires a non-empty string

  LLM_DEFAULT_PROVIDER=firework_ai_api        # fallback when a model id's
                                              # prefix isn't recognised
  LLM_FAST_MODEL=Qwen-3-14B              # alias: "fast"
  LLM_DEFAULT_MODEL=Qwen-3.7-plus        # alias: "default"
  LLM_REASONING_MODEL=Qwen-3.7-plus      # alias: "reasoning"

  To move the whole app to a AMD-hosted model:
    VLLM_BASE_URL=http://<host>:8000/v1    

  Qwen 3.7 Plus is a hybrid-reasoning model (thinking / non-thinking modes
  in one checkpoint). complete()/complete_json() accept an optional
  `reasoning_effort` kwarg ("none" | "low" | "medium" | "high").
  Self-hosted Qwen3 via vLLM doesn't accept a top-level `reasoning_effort` 
  field at all — VLLMProvider translates it into vLLM's 
  `chat_template_kwargs: {"enable_thinking": bool}` shape
  internally, so call sites use the same kwarg either way.

═══════════════════════════════════════════════════════════════════════════
ADDING A NEW PROVIDER
  Subclass LLMProvider, implement `complete()` and `is_configured`, register
  it in `_get_provider()` and add its model-id prefixes to `_PREFIX_TO_PROVIDER`.
  That's the entire surface area — nothing else in the file changes.
═══════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from dotenv import load_dotenv

load_dotenv()


# ════════════════════════════════════════════════════════════════════════
# PUBLIC RESPONSE TYPE / ERRORS
# ════════════════════════════════════════════════════════════════════════

@dataclass
class LLMResponse:
    """What every provider hands back internally. Callers normally just use
    gateway.complete()'s plain-string return — this is exposed in case an
    engine ever needs the raw SDK response (token usage, finish_reason, etc)."""
    text: str
    provider: str
    model: str
    truncated: bool = False
    raw: Any = field(default=None, repr=False)


class LLMGatewayError(RuntimeError):
    """Raised for any gateway-level failure: missing API key, unknown
    provider, or unknown model. Engines can catch this the same way
    routes.py already catches missing-client errors today."""


# ════════════════════════════════════════════════════════════════════════
#    PROVIDER INTERFACE
#    Every backend implements this and nothing else. Engine files
#    never see these classes directly — only the functions in section 4 do.
# ════════════════════════════════════════════════════════════════════════

class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def complete(
        self,
        messages: List[Dict[str, str]],
        *,
        model: str,
        system: Optional[str],
        max_tokens: int,
        temperature: float,
        response_format: Literal["text", "json"] = "text",
        reasoning_effort: Optional[str] = None,
    ) -> LLMResponse:
        ...

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        ...


# ── OpenAI ──────────────────────────────────────────────────────────────
class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        from openai import AsyncOpenAI  # local import — don't require the SDK if unused
        self._api_key = api_key or os.getenv("OPENAI_KEY")
        self._client = (
            AsyncOpenAI(api_key=self._api_key, base_url=base_url) if self._api_key else None
        )

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    async def complete(self, messages, *, model, system, max_tokens, temperature, response_format="text", reasoning_effort=None) -> LLMResponse:
        if not self._client:
            raise LLMGatewayError("OPENAI_API_KEY not configured.")
        full_messages = ([{"role": "system", "content": system}] if system else []) + messages
        kwargs: Dict[str, Any] = dict(
            model=model,
            messages=full_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}
        if reasoning_effort is not None:
            # Only o-series models accept this — callers are responsible for
            # not sending it to gpt-4o-mini etc. (see complete()'s docstring).
            kwargs["reasoning_effort"] = reasoning_effort
        resp = await self._client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        return LLMResponse(
            text=choice.message.content or "",
            provider=self.name,
            model=model,
            truncated=(choice.finish_reason == "length"),
            raw=resp,
        )


# Fireworks (hosted — Qwen 3.7 Plus)
class FireworksProvider(LLMProvider):
    """
    Fireworks AI's managed inference API. OpenAI-compatible on the wire, so
    it reuses the AsyncOpenAI client with a different base_url/api_key.
    """
    name = "fireworks"

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        from openai import AsyncOpenAI
        self._api_key = api_key or os.getenv("FIREWORKS_API_KEY")
        self._base_url = base_url or os.getenv(
            "FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1"
        )
        self._client = (
            AsyncOpenAI(api_key=self._api_key, base_url=self._base_url) if self._api_key else None
        )

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    async def complete(self, messages, *, model, system, max_tokens, temperature, response_format="text", reasoning_effort=None) -> LLMResponse:
        if not self._client:
            raise LLMGatewayError("FIREWORKS_API_KEY not configured.")
        full_messages = ([{"role": "system", "content": system}] if system else []) + messages
        kwargs: Dict[str, Any] = dict(
            model=model,
            messages=full_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if response_format == "json":
            # Honoured by Fireworks for JSON-mode-capable models (Maverick,
            # Qwen 3.7 Plus included); silently ignored otherwise, same as
            # OpenAIProvider.
            kwargs["response_format"] = {"type": "json_object"}
        if reasoning_effort is not None:
            # Hybrid-reasoning models (e.g. Qwen 3.7 Plus) accept
            # "none" | "low" | "medium" | "high" to toggle/tune thinking
            # mode. Non-reasoning Fireworks models will error on this —
            # only pass it for models that support it.
            kwargs["reasoning_effort"] = reasoning_effort
        resp = await self._client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        return LLMResponse(
            text=choice.message.content or "",
            provider=self.name,
            model=model,
            truncated=(choice.finish_reason == "length"),
            raw=resp,
        )


# ── Self-hosted vLLM (e.g. the AMD-GPU notebook) ────────────────────────
class VLLMProvider(LLMProvider):
    """
    Self-hosted vLLM instance — OpenAI-compatible on the wire (vLLM exposes
    /v1/chat/completions), so this reuses AsyncOpenAI pointed at
    VLLM_BASE_URL instead of api.openai.com. vLLM doesn't check the API key
    by default; the SDK still requires a non-empty string, hence "EMPTY".

    IMPORTANT — thinking mode: unlike Fireworks' qwen3p7 (which accepts a
    top-level `reasoning_effort` field), vLLM's OpenAI-compatible server
    toggles Qwen3's hybrid thinking mode via
    `extra_body={"chat_template_kwargs": {"enable_thinking": bool}}`.
    complete() below does that translation so callers keep using the same
    `reasoning_effort` kwarg regardless of provider. Also: if the vLLM
    process wasn't launched with `--reasoning-parser qwen3`, an enabled
    <think>...</think> block comes back inline inside message.content
    rather than in a separate field — this is exactly why "qwen/" is
    registered in _HYBRID_REASONING_MODEL_PREFIXES below, so
    reasoning_effort defaults to "none" unless a caller opts in.
    """
    name = "vllm"

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        from openai import AsyncOpenAI
        self._base_url = base_url or os.getenv("VLLM_BASE_URL")
        self._api_key = api_key or os.getenv("VLLM_API_KEY", "EMPTY")
        self._client = (
            AsyncOpenAI(api_key=self._api_key, base_url=self._base_url) if self._base_url else None
        )

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    async def complete(self, messages, *, model, system, max_tokens, temperature, response_format="text", reasoning_effort=None) -> LLMResponse:
        if not self._client:
            raise LLMGatewayError("VLLM_BASE_URL not configured.")
        full_messages = ([{"role": "system", "content": system}] if system else []) + messages
        kwargs: Dict[str, Any] = dict(
            model=model,
            messages=full_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}
        if reasoning_effort is not None:
            # vLLM/Qwen3 has no top-level reasoning_effort field — thinking
            # mode is a chat-template flag, passed through extra_body.
            kwargs["extra_body"] = {
                "chat_template_kwargs": {"enable_thinking": reasoning_effort != "none"}
            }
        resp = await self._client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        return LLMResponse(
            text=choice.message.content or "",
            provider=self.name,
            model=model,
            truncated=(choice.finish_reason == "length"),
            raw=resp,
        )


# ════════════════════════════════════════════════════════════════════════
# ROUTING — model name → provider  (see module docstring for rationale)
# ════════════════════════════════════════════════════════════════════════

ALIASES: Dict[str, str] = {
    "fast":      os.getenv("LLM_FAST_MODEL", "gpt-4o-mini"),
    "default":   os.getenv("LLM_DEFAULT_MODEL", "gpt-4o-mini"),
    "reasoning": os.getenv("LLM_REASONING_MODEL", "gpt-4o-mini"),
}

# Order matters: first matching prefix wins.
_PREFIX_TO_PROVIDER: List[Tuple[str, str]] = [
    ("gpt-",       "openai"),
    ("o1",         "openai"),
    ("o3",         "openai"),
    ("chatgpt-",   "openai"),
    ("accounts/fireworks/", "fireworks"),
    ("qwen/",      "vllm"),
]

DEFAULT_PROVIDER = os.getenv("LLM_DEFAULT_PROVIDER", "openai")

# Hybrid-reasoning models that think by default unless told not to. gpt-4o-mini
# never thought, so every call site written against it assumed the full
# max_tokens budget goes to the actual answer. Swapping in one of these models
# without setting reasoning_effort silently breaks that assumption — thinking
# tokens eat the budget first and short-max_tokens calls truncate before the
# real answer is written. Default these to reasoning_effort="none" unless a
# caller explicitly asks for thinking, so behavior matches what call sites
# were written expecting. Add new hybrid-reasoning model prefixes here as you
# adopt them.
_HYBRID_REASONING_MODEL_PREFIXES: Tuple[str, ...] = (
    "accounts/fireworks/models/qwen3p7-",
    "qwen/",
)


def _default_reasoning_effort(model: str) -> Optional[str]:
    lowered = model.lower()
    if any(lowered.startswith(p) for p in _HYBRID_REASONING_MODEL_PREFIXES):
        return "none"
    return None


def _provider_for_model(model: str) -> str:
    lowered = model.lower()
    for prefix, provider in _PREFIX_TO_PROVIDER:
        if lowered.startswith(prefix):
            return provider
    return DEFAULT_PROVIDER


@lru_cache(maxsize=None)
def _get_provider(name: str) -> LLMProvider:
    """Providers are instantiated lazily and cached — you only pay the SDK
    import / client-construction cost for providers you actually call."""
    if name == "openai":
        return OpenAIProvider()
    if name == "fireworks":
        return FireworksProvider()
    raise LLMGatewayError(f"Unknown LLM provider '{name}'.")


def resolve_model(model: Optional[str]) -> str:
    """alias or None -> concrete model id. Literal model ids pass through
    unchanged, so existing `model="gpt-4o-mini"` callers keep working."""
    if not model:
        return ALIASES["default"]
    return ALIASES.get(model, model)


# ════════════════════════════════════════════════════════════════════════
# PUBLIC API — the only surface engine files touch
# ════════════════════════════════════════════════════════════════════════

async def complete(
    messages: Union[List[Dict[str, str]], str],
    *,
    model: Optional[str] = None,
    system: Optional[str] = None,
    max_tokens: int = 1000,
    temperature: float = 0.5,
    response_format: Literal["text", "json"] = "text",
    reasoning_effort: Optional[str] = None,
) -> str:
    """
    The one function every engine calls instead of touching an openai
    client directly.

    messages: either a plain prompt string, or a full
              [{"role": "user"/"assistant", "content": "..."}] list. Put the
              system prompt in `system`, never inline in `messages` —
              providers differ on how system prompts are passed and the
              gateway normalises that for you.
    model:    a logical alias ("fast" / "default" / "reasoning") OR a literal
              vendor model id ("gpt-4o-mini",
              "accounts/fireworks/models/qwen3p7-plus").
              Omit it to use the configured default.
    response_format: "json" requests the provider's native JSON-object mode
              where one exists (OpenAI, Fireworks).
    reasoning_effort: "none" | "low" | "medium" | "high" — only forward this
              for models that actually support hybrid/tunable reasoning
              (e.g. "accounts/fireworks/models/qwen3p7-plus", OpenAI's
              o-series). Leave it unset for gpt-4o-mini or non-reasoning
              Fireworks models; they'll error if you send it.
              For known hybrid-reasoning models, omitting this defaults to
              "none" (see _default_reasoning_effort) — those models think by
              default, and an unset budget-sized max_tokens written for a
              non-reasoning model will truncate before the real answer if
              thinking isn't turned off. Pass "low"/"medium"/"high"
              explicitly to opt a specific call into thinking mode.

    Returns plain text. Raises LLMGatewayError if the resolved provider
    isn't configured (missing API key), the call fails, or the response was
    truncated (finish_reason == "length") — a truncated response is almost
    never useful and surfacing it here beats every engine re-deriving "was
    this cut off?" from a raw SDK response.
    """
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]

    concrete_model = resolve_model(model)
    provider_name = _provider_for_model(concrete_model)
    provider = _get_provider(provider_name)

    if reasoning_effort is None:
        # Caller didn't ask for a specific thinking level — fall back to
        # "none" for models that think by default, so behavior matches
        # what call sites written against non-reasoning models expect.
        # Explicitly pass reasoning_effort="low"/"medium"/"high" to opt in.
        reasoning_effort = _default_reasoning_effort(concrete_model)

    response = await provider.complete(
        messages,
        model=concrete_model,
        system=system,
        max_tokens=max_tokens,
        temperature=temperature,
        response_format=response_format,
        reasoning_effort=reasoning_effort,
    )
    if response.truncated:
        raise LLMGatewayError(
            f"Model response was truncated at max_tokens={max_tokens} "
            f"(provider={response.provider}, model={response.model}). "
            "Increase max_tokens or reduce the request scope and retry."
        )
    return response.text


_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)```$", re.DOTALL)


def _strip_fences(raw: str) -> str:
    """Remove accidental ```json … ``` fences from model output."""
    m = _FENCE_RE.match(raw.strip())
    return m.group(1).strip() if m else raw.strip()


async def complete_json(
    messages: Union[List[Dict[str, str]], str],
    *,
    model: Optional[str] = None,
    system: Optional[str] = None,
    max_tokens: int = 1000,
    temperature: float = 0.3,
    response_format: Literal["text", "json"] = "json",
    reasoning_effort: Optional[str] = None,
) -> Any:
    """
    Same as complete(), but strips ```json fences and json.loads()s the
    result. Every engine that currently does:

        resp = await openai_client.chat.completions.create(..., response_format={"type": "json_object"})
        json.loads(_strip_fences(resp.choices[0].message.content))

    collapses to a single call to this function. response_format defaults to
    "json" (use the provider's native JSON mode where available) since that's
    this function's entire purpose — pass response_format="text" to opt out
    for a provider that mishandles it.

    Raises json.JSONDecodeError on malformed model output, or
    LLMGatewayError if the response was truncated before parsing is even
    attempted — callers already catch both today (routes.py), so behaviour
    is unchanged.
    """
    raw = await complete(
        messages, model=model, system=system,
        max_tokens=max_tokens, temperature=temperature,
        response_format=response_format, reasoning_effort=reasoning_effort,
    )
    return json.loads(_strip_fences(raw))


def is_ready(model: Optional[str] = None) -> bool:
    """
    Replaces the `openai_client is not None` checks scattered through
    routes.py (_assert_client(), the /health route's "ai" field, etc).
    Reports whether the provider that would actually serve `model` (or the
    configured default, if omitted) has its API key/endpoint configured.
    """
    try:
        provider_name = _provider_for_model(resolve_model(model))
        return _get_provider(provider_name).is_configured
    except LLMGatewayError:
        return False


# ════════════════════════════════════════════════════════════════════════
# SELF-TEST — run `python -m agents.llm_gateway` to sanity-check which
#    providers are configured, without touching any other file.
# ════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import asyncio

    # Fallback model id to use when a configured provider isn't targeted by
    # any of the fast/default/reasoning aliases — e.g. you've set
    # LLM_DEFAULT_MODEL to an OpenAI id but left FIREWORKS_API_KEY set too.
    # Without this, a configured-but-unaliased provider would be silently
    # skipped instead of actually being exercised.
    _PROBE_MODEL_FALLBACK: Dict[str, str] = {
        "openai":    "gpt-4o-mini",
        "fireworks": "accounts/fireworks/models/qwen3p7-plus",
        "vllm":      "Qwen/Qwen3-14B",
    }

    def _probe_model_for(provider_name: str) -> Optional[str]:
        for alias in ("default", "fast", "reasoning"):
            model = ALIASES[alias]
            if _provider_for_model(model) == provider_name:
                return model
        return _PROBE_MODEL_FALLBACK.get(provider_name)

    async def _smoke_test():
        for alias in ("fast", "default", "reasoning"):
            model = ALIASES[alias]
            provider = _provider_for_model(model)
            ready = is_ready(alias)
            print(f"  alias={alias:<10} model={model:<24} provider={provider:<10} configured={ready}")

        configured = []
        for name in ("openai", "fireworks", "vllm"):
            try:
                if _get_provider(name).is_configured:
                    configured.append(name)
            except LLMGatewayError:
                pass
        if not configured:
            print("\nNo provider configured — set an API key/endpoint in .env to test a live call.")
            return

        # Exercise every configured provider, not just the first one found —
        # "configured" only means an API key is present, not that the
        # credentials are valid or the model is actually invocable, so a
        # provider further down the list silently going unprobed is exactly
        # the kind of false confidence this smoke test exists to catch.

        for name in configured:
            probe_model = _probe_model_for(name)
            if probe_model is None:
                print(f"\nSkipping '{name}': configured, but no alias points at it and "
                      f"there's no default probe model for it. Test it explicitly, "
                      f"e.g. complete(..., model='<your-{name}-model-id>').")
                continue
            print(f"\nFiring a live test call against '{name}' (model={probe_model})...")
            try:
                text = await complete("Reply with exactly one word: OK", model=probe_model)
                print(f"  → {text!r}")
            except Exception as e:
                print(f"  ✗ FAILED: {type(e).__name__}: {e}")

    print("LLM Gateway — configured providers:\n")
    asyncio.run(_smoke_test())