"""
Lumina Real-Time Voice Engine
═══════════════════════════════════════════════════════════════════════════
PURPOSE
  Turns a TEACHER_SAYS narration string into an actual streamed teacher
  *voice* — real synthesized speech arriving chunk by chunk in real time —
  and a word-reveal that is derived FROM that real audio, not guessed.

WHY THIS EXISTS
  streaming_engine.py used to fake a teacher's voice. `_stream_text_chunks()`
  released one word every fixed 0.55s, forever, no matter the word. That's
  a metronome, not a teacher. Real speech speeds through short connective
  words ("and", "so", "the — "), slows on technical terms, and never once
  hits a perfectly even pace. A hardcoded per-word sleep can't do that, and
  worse, there was no actual sound — the "voice" was silence with subtitles.

  voice_engine.py fixes both problems at once by making the AUDIO the
  pacing clock. We stream real TTS audio from OpenAI's gpt-4o-mini-tts,
  and because raw PCM has a fixed, known byte rate, we can convert
  "bytes received so far" into "seconds of speech already generated" with
  no guesswork. Each word is released the instant the audio stream reaches
  that word's estimated onset. Text and voice now share one clock instead
  of running on two unrelated timers that happen to look similar.

ARCHITECTURE
  stream_narration(text, role) is the single entry point:

    1.  Splits `text` into speakable clauses on punctuation. This keeps
        each OpenAI TTS round-trip short, so the first sound reaches the
        learner fast instead of the whole narration going silent while a
        long paragraph synthesizes.
    2.  For each clause, opens a streaming TTS response and reads raw PCM
        as it arrives.
    3.  A running byte counter is converted to elapsed seconds (byte_rate
        is fixed for PCM16 mono), and words are released the moment the
        audio clock passes their estimated onset — modeled from character
        length, not a flat per-word count.
    4.  Interleaved "word" and "audio" events are yielded in the exact
        order they become due.

  streaming_engine.py turns "word" events into TEACHER_SAYS (unchanged
  contract with the frontend) and "audio" events into a new
  TEACHER_AUDIO_CHUNK SSE event carrying base64 PCM for a Web Audio /
  MediaSource player on the client.

FAILURE MODE
  If synthesis fails (network, quota, API error) for a clause, that clause
  falls back to a silent, evenly-paced word release so the lesson keeps
  moving — a lesson must never hard-stop because a voice call hiccuped.
  An "audio_error" event is emitted so the caller can log/observe it.

TEACHER VOICE DIRECTION
  gpt-4o-mini-tts accepts free-text `instructions` describing HOW to say
  the input. We select an instruction preset from the narration's `role`
  ("opener", "transition", "bridge", "encouragement", "explanation") so a
  resume bridge sounds warmer than a mid-derivation aside, and a worked
  step sounds measured rather than breathless. This is Lumina's vocal
  personality layer — the same teacher, adjusting register the way a
  real one does without changing who they are.
"""

from __future__ import annotations

import asyncio
import base64
import re
from typing import AsyncGenerator, Callable, Dict, List, Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI

import time

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

TTS_MODEL:     str = "gpt-4o-mini-tts"
DEFAULT_VOICE: str = "shimmer"

# PCM16 mono @ 24kHz — OpenAI's streaming TTS output for response_format="pcm".
SAMPLE_RATE_HZ:    int   = 24000
BYTES_PER_SAMPLE:  int   = 2
BYTE_RATE:         float = SAMPLE_RATE_HZ * BYTES_PER_SAMPLE  # bytes / second

# Frontend-facing audio chunk size. ~300ms at 24kHz/16-bit mono.
# NOTE: this was 4800 bytes (~100ms). At 100ms, a multi-second clause
# creates dozens of AudioBufferSourceNodes on the frontend, and small
# per-chunk network/SSE jitter is enough to starve the player's queue
# between them — heard as clicks/stutter even though the underlying TTS
# audio itself is continuous. 300ms is a middle ground: few enough nodes
# to schedule smoothly, still short enough that "first sound" latency
# stays low. If the frontend player buffers ahead (recommended: 300-500ms
# of lookahead before playback starts), this can go higher still.
AUDIO_CHUNK_BYTES: int = 14400

# Character-weighted word duration model (see _estimate_word_durations).
_BASE_WORD_SECONDS: float = 0.16    # floor duration for the shortest word
_PER_CHAR_SECONDS:  float = 0.045   # additional seconds per character

# Clause boundaries: split after SENTENCE-ending punctuation + whitespace
# only. Commas, semicolons, colons, and dashes are deliberately NOT split
# points — they're mid-sentence pauses, and a comma-fragment like "First,"
# handed to the TTS model as a complete, isolated utterance has nothing to
# continue into. Short trailing-punctuation fragments like that are a known
# trigger for these models to glitch or literally vocalize the punctuation
# instead of just pausing on it. Keeping commas inside their clause lets the
# model handle the pause the way it's designed to, with real context on
# both sides of it.
_CLAUSE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")

# Safety valve for latency, not naturalness: if a single (comma-free-split)
# sentence is unusually long, "first sound" would be delayed too much
# waiting for the whole thing to synthesize. Only in that case do we allow
# a secondary split — at a comma, near the midpoint — so long sentences
# still stream quickly without fragmenting every normal sentence.
_MAX_CLAUSE_CHARS: int = 220

# The other end of the same problem: a short sentence ("Good." "Let's
# continue.") sent to TTS as its own isolated call is the worst-case input
# for this model — barely enough audio for it to find its footing, plus a
# fresh synthesis "cold start" (and network round-trip) every couple of
# words. Sentences are merged with their neighbors until they clear this
# floor, so a run of short sentences becomes one natural-sounding call
# instead of several stub calls stitched together.
_MIN_CLAUSE_CHARS: int = 45

# Silent fallback pacing if a clause's TTS call fails outright.
_FALLBACK_WORD_DELAY_S: float = 0.32

_client: Optional[AsyncOpenAI] = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI()
    return _client


# ─────────────────────────────────────────────────────────────────────────────
# VOICE DIRECTION PRESETS  (keyed to the same `role` values streaming_engine
# already attaches to TEACHER_SAYS payloads: opener / transition / bridge /
# explanation / encouragement)
# ─────────────────────────────────────────────────────────────────────────────

_INSTRUCTION_PRESETS: Dict[str, str] = {
    "opener": (
        "Warm, confident classroom teacher welcoming a student into a lesson. "
        "Unhurried and inviting, like the start of a class they're glad to be in."
    ),
    "bridge": (
        "A teacher stepping back into the lesson right after answering a "
        "student's question or acknowledging their attempt. Warm, reassuring, "
        "and forward-moving — never flat, never a re-read."
    ),
    "transition": (
        "A teacher moving fluidly from one idea straight into the next, in the "
        "same breath. Light, connective, a little quicker — a handshake between "
        "ideas, not a new announcement."
    ),
    "explanation": (
        "A calm, precise teacher walking through reasoning on a board in real "
        "time. Measured pace, gentle emphasis on key terms, natural micro-pauses "
        "at commas and before results."
    ),
    "encouragement": (
        "A patient, kind mentor responding to a student's attempt. Genuinely "
        "warm, never patronizing, steady."
    ),
    "default": (
        "A warm, articulate teacher speaking live to one student. Natural "
        "contractions, natural pacing, never robotic."
    ),
}


def _instructions_for(role: Optional[str]) -> str:
    return _INSTRUCTION_PRESETS.get(role or "default", _INSTRUCTION_PRESETS["default"])


# ─────────────────────────────────────────────────────────────────────────────
# DEFENSIVE TEXT SANITIZATION
# ─────────────────────────────────────────────────────────────────────────────
#
# This module has no visibility into how narration text was produced —
# it just gets a string and speaks it. lesson_engine.py's prompt is
# supposed to guarantee SPEAK content is clean, natural language (no
# LaTeX, no raw unicode math glyphs), but that's an upstream contract,
# not something this file can enforce. If it's ever violated — a stray
# "$", a "\text{...}" macro, or a mojibake-corrupted symbol (e.g. "→"
# arriving as "â†'" after a UTF-8-as-Latin-1 misdecode upstream) — the
# TTS model will happily read it aloud verbatim: "dollar sign", "backslash
# text open brace", or a garbled string of syllables for the mojibake
# bytes. None of that is a "quirky teacher voice"; it's dead give-away
# that something upstream broke. Sanitize defensively so a narration bug
# degrades to *slightly plainer speech* instead of a broken-sounding one.
_MOJIBAKE_HINT = re.compile(r"[ÃÂ][\x80-\xbf]")  # classic UTF-8-as-Latin-1 tell
_LATEX_WRAPPED  = re.compile(r"\\(text|boxed|mathrm|mathbf)\{([^{}]*)\}")
_LATEX_COMMAND  = re.compile(r"\\[a-zA-Z]+")
_LATEX_DELIMS   = re.compile(r"\\[()\[\]]")
_DOLLAR_DELIM   = re.compile(r"\${1,2}")

_SYMBOL_WORDS = {
    "→": "leads to", "×": "times", "≠": "is not equal to",
    "≤": "at most", "≥": "at least", "±": "plus or minus",
    "✓": "", "✗": "", "âœ“": "", "âœ—": "", "â†'": "leads to",
}


def _sanitize_for_speech(text: str) -> str:
    """
    Best-effort cleanup before text reaches TTS. Never raises — a failed
    repair should fall through to the original text rather than block
    narration.
    """
    if not text:
        return text

    cleaned = text

    # Attempt to repair classic mojibake (UTF-8 bytes misdecoded as
    # Latin-1/CP1252 upstream, e.g. "→" -> "â†'"). Only attempt this when
    # the telltale byte pattern is present, and only keep the result if
    # the round-trip actually succeeds.
    if _MOJIBAKE_HINT.search(cleaned):
        try:
            repaired = cleaned.encode("latin-1").decode("utf-8")
            cleaned = repaired
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass

    # Spell out or drop any remaining raw symbol glyphs rather than let
    # the TTS model sound them out letter-by-letter.
    for symbol, replacement in _SYMBOL_WORDS.items():
        if symbol in cleaned:
            # Pad with spaces so e.g. "8 →y" doesn't become "8 leads toy".
            cleaned = cleaned.replace(symbol, f" {replacement} " if replacement else " ")

    # Unwrap simple LaTeX wrappers to their inner text: "\text{Step 2}"
    # -> "Step 2" — speak the content, not the macro name.
    cleaned = _LATEX_WRAPPED.sub(lambda m: m.group(2), cleaned)

    # Strip any remaining LaTeX commands/delimiters and stray "$" signs
    # that slipped through — better silent than spoken as "backslash" /
    # "dollar sign".
    cleaned = _LATEX_DELIMS.sub("", cleaned)
    cleaned = _LATEX_COMMAND.sub("", cleaned)
    cleaned = _DOLLAR_DELIM.sub("", cleaned)
    cleaned = cleaned.replace("{", "").replace("}", "")

    return re.sub(r"\s+", " ", cleaned).strip()


# ─────────────────────────────────────────────────────────────────────────────
# WORD TIMING MODEL
# ─────────────────────────────────────────────────────────────────────────────

def _estimate_word_durations(words: List[str]) -> List[float]:
    """
    Estimate how long each word takes to say, from its character length.
    Not phoneme-accurate, but far closer to real speech than "every word
    is 0.55s": "a" and "extraordinarily" are not spoken in the same time,
    and this model at least knows that much.
    """
    durations = []
    for w in words:
        clean = re.sub(r"[^\w]", "", w)
        durations.append(_BASE_WORD_SECONDS + _PER_CHAR_SECONDS * len(clean))
    return durations


def _cumulative_onsets(words: List[str]) -> List[float]:
    """Seconds-from-clause-start at which each word should be revealed."""
    onsets, total = [], 0.0
    for d in _estimate_word_durations(words):
        onsets.append(total)
        total += d
    return onsets


def estimate_total_duration_s(text: str) -> float:
    """
    Best-effort upfront estimate of how long the FULL `text` will take to
    speak, using the same character-weighted word model as clause-internal
    onset pacing.

    This is the single source of truth for that estimate. Callers that need
    to plan around narration length — e.g. streaming_engine.py pacing a
    concurrent BOARD_WRITE against a SPEAK event — must call this instead
    of re-deriving the 0.16/0.045 formula themselves. Two independent
    copies of the same "model" drift the moment one file's constants get
    tuned and the other's don't. That drift alone wasn't the real bug
    (see stream_narration's "progress" events for the actual fix below),
    but letting it happen for no reason was an unforced error worth closing.
    """
    return sum(_estimate_word_durations(_sanitize_for_speech(text).split()))


def _split_clauses(text: str) -> List[str]:
    """
    Break narration into speakable clauses so each TTS round-trip stays
    natural-sounding: sentence-bounded (never mid-sentence, see
    _CLAUSE_BOUNDARY), long enough that the model has real speech to work
    with (_MIN_CLAUSE_CHARS), and short enough that first sound isn't
    delayed too long on very long sentences (_MAX_CLAUSE_CHARS).
    """
    text = text.strip()
    if not text:
        return []
    sentences = [p.strip() for p in _CLAUSE_BOUNDARY.split(text) if p.strip()]
    sentences = sentences or [text]

    # Merge a run of short sentences into one clause until it clears the
    # floor, so "Good." doesn't become its own TTS call.
    merged: List[str] = []
    buffer = ""
    for sentence in sentences:
        buffer = f"{buffer} {sentence}".strip() if buffer else sentence
        if len(buffer) >= _MIN_CLAUSE_CHARS:
            merged.append(buffer)
            buffer = ""
    if buffer:
        # Leftover short tail: fold into the previous clause rather than
        # shipping it alone, unless it's the only thing we have.
        if merged:
            merged[-1] = f"{merged[-1]} {buffer}".strip()
        else:
            merged.append(buffer)

    # Only clauses that are still too long (after merging) get a secondary
    # split, and only at a comma near the midpoint (not every comma) — one
    # extra seam in a long clause is an acceptable latency tradeoff; one
    # seam per comma is not.
    out: List[str] = []
    for part in merged:
        if len(part) <= _MAX_CLAUSE_CHARS:
            out.append(part)
            continue
        midpoint = len(part) // 2
        comma_positions = [m.start() for m in re.finditer(r",\s+", part)]
        split_at = min(comma_positions, key=lambda i: abs(i - midpoint), default=None) \
            if comma_positions else None
        if split_at is None:
            out.append(part)
        else:
            out.append(part[: split_at + 1].strip())
            out.append(part[split_at + 1:].strip())

    return out


# ─────────────────────────────────────────────────────────────────────────────
# CORE: ONE CLAUSE — AUDIO AND WORDS SHARE ONE CLOCK
# ─────────────────────────────────────────────────────────────────────────────
async def _speak_clause(
    clause:       str,
    voice:        str,
    instructions: str,
    queue:        "asyncio.Queue[Optional[Dict]]",
    elapsed_base: float = 0.0,
) -> None:
    words  = clause.split()
    onsets = _cumulative_onsets(words)

    bytes_received = 0
    next_word_idx  = 0
    clause_start   = time.time()

    async def _release_due_words(audio_elapsed_s: float) -> None:
        # Gate on BOTH conditions: the audio has actually been generated
        # this far (audio_elapsed_s, from real PCM byte count — accurate,
        # but now arrives at network speed) AND real wall-clock time has
        # reached the word's estimated onset. The sleep here paces WORD
        # RELEASE only — it never blocks audio bytes from shipping.
        nonlocal next_word_idx
        while next_word_idx < len(words) and onsets[next_word_idx] <= audio_elapsed_s:
            wall_elapsed = time.time() - clause_start
            target       = onsets[next_word_idx]
            if target > wall_elapsed:
                await asyncio.sleep(target - wall_elapsed)
            await queue.put({"kind": "word", "text": words[next_word_idx]})
            # Report progress from THIS point — after the real-time sleep
            # above — not from raw audio_elapsed_s. OpenAI can stream a
            # clause's PCM faster than real playback speed (a 3-second
            # clause arriving in well under a second), so audio_elapsed_s
            # alone races ahead of what a listener has actually heard.
            # A caller pacing something else against this narration (e.g.
            # streaming_engine's synced BOARD_WRITE) needs the same
            # real-time-gated clock words already use, or it "catches up"
            # in a burst the instant a batch of bytes lands — visible as
            # board content flashing in all at once instead of tracking
            # the voice smoothly.
            await queue.put({
                "kind":      "progress",
                "elapsed_s": elapsed_base + max(target, time.time() - clause_start),
            })
            next_word_idx += 1

    try:
        client = _get_client()
        async with client.audio.speech.with_streaming_response.create(
            model=TTS_MODEL,
            voice=voice,
            input=clause,
            response_format="pcm",
        ) as response:
            buf = bytearray()

            async for raw in response.iter_bytes():
                if not raw:
                    continue
                buf.extend(raw)
                bytes_received += len(raw)
                audio_elapsed_s = bytes_received / BYTE_RATE

                # Audio ships the instant it's available — no throttle.
                while len(buf) >= AUDIO_CHUNK_BYTES:
                    chunk = bytes(buf[:AUDIO_CHUNK_BYTES])
                    del buf[:AUDIO_CHUNK_BYTES]
                    await queue.put({
                        "kind":        "audio",
                        "data":        base64.b64encode(chunk).decode("ascii"),
                        "format":      "pcm_s16le",
                        "sample_rate": SAMPLE_RATE_HZ,
                    })

                # Words (and, with them, "progress" events) are paced
                # separately, on their own real-time-gated clock — see
                # _release_due_words.
                await _release_due_words(audio_elapsed_s)

            if buf:
                await queue.put({
                    "kind":        "audio",
                    "data":        base64.b64encode(bytes(buf)).decode("ascii"),
                    "format":      "pcm_s16le",
                    "sample_rate": SAMPLE_RATE_HZ,
                })

        # Release any trailing words, then hold the clause open until real
        # time catches up to its estimated speech duration. This is what
        # keeps _speak_clause() — and therefore the SPEAK event, and
        # therefore anything gated behind it in _deliver_step (WRITE,
        # PAUSE, AWAIT_RESPONSE) — from completing before the client would
        # realistically have finished playing this clause's audio.
        total_duration = max(bytes_received / BYTE_RATE, onsets[-1] if onsets else 0.0)
        await _release_due_words(total_duration + 0.25)
        remaining = total_duration - (time.time() - clause_start)
        if remaining > 0:
            await asyncio.sleep(remaining)
        await queue.put({"kind": "progress", "elapsed_s": elapsed_base + total_duration})

    except Exception as exc:  # noqa: BLE001
        fallback_start = time.time()
        for w in words[next_word_idx:]:
            await queue.put({"kind": "word", "text": w})
            await asyncio.sleep(_FALLBACK_WORD_DELAY_S)
            await queue.put({
                "kind":      "progress",
                "elapsed_s": elapsed_base + (time.time() - fallback_start),
            })
        await queue.put({"kind": "audio_error", "message": str(exc)})

    finally:
        await queue.put(None)

async def stream_narration(
    text:       str,
    role:       Optional[str] = None,
    voice:      str = DEFAULT_VOICE,
    stop_check: Optional[Callable[[], bool]] = None,
) -> AsyncGenerator[Dict, None]:
    """
    Public entry point. Streams one teacher narration as interleaved events,
    in the order they're actually due:

      {"kind": "word",  "text": "Let"}
      {"kind": "audio", "data": "<base64 pcm16>", "format": "pcm_s16le",
       "sample_rate": 24000}
      {"kind": "progress", "elapsed_s": 1.84}
      {"kind": "progress", "elapsed_s": 0.0, "total_estimate_s": 6.2}  (first event only)
      ...
      {"kind": "audio_error", "message": "..."}   — only if a clause's
                                                      TTS call failed

    `role` selects the vocal register (see _INSTRUCTION_PRESETS) — pass
    the same role streaming_engine already stamps onto TEACHER_SAYS
    payloads ("opener", "transition", "bridge", "explanation", ...).

    PROGRESS EVENTS — this is the fix for a real WRITE/SPEAK desync bug,
    not just bookkeeping. A caller that runs a BOARD_WRITE concurrently
    with this narration (lesson_engine's sync_with_previous) used to plan
    the board's entire char-reveal pace from ONE upfront duration estimate,
    computed before a single byte of real TTS audio existed. Real speech
    doesn't match that estimate exactly — different clauses speed up,
    slow down, and get merged/split (see _MIN_CLAUSE_CHARS/_MAX_CLAUSE_CHARS)
    in ways the estimate can't see coming — so the board would finish
    writing while the voice was still talking, or keep scratching away
    after the voice had already stopped. Both read as "glitching" the
    instant WRITE and SPEAK overlap.

    "progress" events fix that by giving the caller a LIVE, continuously-
    updating clock instead of a one-shot guess: the very first event
    carries `total_estimate_s` (the word-model estimate for the *entire*
    narration, from `estimate_total_duration_s`), and every event after
    that carries the REAL cumulative `elapsed_s` — driven by actual bytes
    received from TTS, exactly like the word-release clock inside
    `_speak_clause` already is. A caller pacing a board write against this
    narration should re-derive its remaining pace from
    `total_estimate_s - elapsed_s` on every chunk, not commit to a number
    once at the start. `elapsed_s` still advances (from the word-model
    estimate, not real audio) even on a failed clause, so it never stalls
    or jumps when TTS falls back to silent pacing mid-narration.

    `stop_check`, if given, is polled ONLY between clauses (e.g.
    `lambda: session._pause_flag.is_set()`). If it returns True, no
    further clauses are started. This is deliberately the ONLY place a
    caller can stop this generator early: a clause's queue, once its TTS
    task is created, always drains to completion. Cancelling mid-clause
    (the previous behaviour, driven by the caller returning early out of
    its own `async for`) throws GeneratorExit here, which cancels
    _speak_clause's task and silently drops whatever PCM was already
    generated but not yet yielded — heard by the learner as the voice
    getting cut off mid-word. A clause is at most ~220 chars (a few
    seconds of speech); finishing it before honouring a pause is a small,
    bounded delay and is worth it to never truncate audio that's already
    been synthesized.

    Clauses are delivered strictly in order: each clause's audio and words
    fully drain before the next clause's TTS call is made. This keeps
    reveal order deterministic and bounds concurrent API calls to one.
    """
    clauses = _split_clauses(_sanitize_for_speech(text))
    if not clauses:
        return

    instructions = _instructions_for(role)

    # Upfront estimate for the WHOLE narration (not just the first clause) —
    # this is the denominator a caller uses to turn later real `elapsed_s`
    # values into "how much is left". It's still just an estimate, which is
    # exactly why it's paired with a live, real-bytes numerator instead of
    # being trusted on its own.
    yield {
        "kind":             "progress",
        "elapsed_s":        0.0,
        "total_estimate_s": estimate_total_duration_s(text),
    }

    elapsed_base = 0.0
    for clause in clauses:
        if stop_check is not None and stop_check():
            return

        queue: "asyncio.Queue[Optional[Dict]]" = asyncio.Queue()
        task = asyncio.create_task(_speak_clause(clause, voice, instructions, queue, elapsed_base))
        try:
            # No early-exit here on `stop_check`: once the task is
            # started, drain it fully. `stop_check` is re-polled at the
            # top of the loop, before the *next* clause's TTS call —
            # that's the only intentional cut point. This try/finally
            # only guards against the caller forcibly closing this
            # generator (e.g. an unhandled exception upstream), so the
            # TTS task is still cleaned up rather than orphaned.
            while True:
                item = await queue.get()
                if item is None:
                    break
                if item.get("kind") == "progress":
                    elapsed_base = item["elapsed_s"]
                yield item
        finally:
            if not task.done():
                task.cancel()
        # Propagate any unexpected task-level exception (network errors
        # inside _speak_clause are already caught; this is a last resort).
        exc = task.exception() if task.done() and not task.cancelled() else None
        if exc:
            yield {"kind": "audio_error", "message": str(exc)}