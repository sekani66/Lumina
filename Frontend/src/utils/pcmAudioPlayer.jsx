export class PCMAudioPlayer {
  constructor() {
    this.audioCtx = null;
    this.nextStartTime = 0;
  }

  // Cushion applied any time playback starts fresh — the first chunk of
  // a clause, or any time the queue drains and restarts. The OLD value
  // here was 0.05s (50ms), which is well inside normal SSE/network
  // jitter: any time chunk delivery stutters even slightly right after a
  // restart point, the gap shows up as an audible click/stutter — and
  // clause boundaries are exactly where a new WRITE group also kicks in,
  // which is why this reads as "glitches when talking while writing."
  // voice_engine.py's own docstring already calls for 300-500ms of
  // lookahead here; this wires that recommendation up.
  static LOOKAHEAD_S = 0.3;

  // Browsers require a user gesture (like a click) to unlock audio.
  // This is called right when the lesson starts.
  ensureContext() {
    if (!this.audioCtx) {
      this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
  }

  enqueueChunk(base64Data, sampleRate = 24000) {
    this.ensureContext();

    try {
      // 1. Decode base64 to binary string
      const binaryString = atob(base64Data);
      const len = binaryString.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      // 2. Convert raw 16-bit PCM (Int16 little-endian) to Web Audio's format (Float32)
      const int16Array = new Int16Array(bytes.buffer);
      const float32Array = new Float32Array(int16Array.length);
      for (let i = 0; i < int16Array.length; i++) {
        // Normalize Int16 range (-32768 to 32767) to Float32 range (-1.0 to 1.0)
        float32Array[i] = int16Array[i] / 32768.0;
      }

      // 3. Create an AudioBuffer
      const audioBuffer = this.audioCtx.createBuffer(1, float32Array.length, sampleRate);
      audioBuffer.getChannelData(0).set(float32Array);

      // 4. Schedule playback seamlessly
      const source = this.audioCtx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(this.audioCtx.destination);

      const currentTime = this.audioCtx.currentTime;

      // If the queue drained (audio paused) — or this is the very first
      // chunk — arm a real lookahead cushion rather than a razor-thin
      // one, so ordinary network/decode jitter on the NEXT chunk doesn't
      // open an audible gap.
      if (this.nextStartTime < currentTime) {
        this.nextStartTime = currentTime + PCMAudioPlayer.LOOKAHEAD_S;
      }

      source.start(this.nextStartTime);
      this.nextStartTime += audioBuffer.duration;
    } catch (err) {
      // A single bad chunk (malformed base64, unexpected buffer shape,
      // an AudioContext op throwing) should degrade to "this chunk is
      // dropped" — never to "the rest of the lesson's audio is dead."
      // Text (TEACHER_SAYS) and the board keep going regardless; losing
      // one ~300ms chunk of audio is a far smaller glitch than silence
      // for the rest of the session.
      console.error('[PCMAudioPlayer] failed to enqueue audio chunk, dropping it:', err);
    }
  }

  // Pause playback in place — suspends the AudioContext clock rather than
  // tearing anything down. Every source is scheduled via source.start()
  // relative to audioCtx.currentTime, so freezing that clock freezes
  // everything at once: whatever's audibly playing stops immediately
  // (the hardware output halts), and every source already scheduled
  // ahead in the lookahead buffer simply waits, since the clock they
  // were scheduled against is now frozen too. Nothing is discarded, so
  // this is safe to call at any routine pause point — unlike stop(),
  // which hard-closes the context and permanently drops anything
  // scheduled ahead of currentTime.
  async pause() {
    if (this.audioCtx && this.audioCtx.state === 'running') {
      await this.audioCtx.suspend();
    }
  }

  // Resumes the AudioContext clock exactly where pause() left it —
  // scheduled sources pick back up with no re-scheduling needed.
  async resume() {
    if (this.audioCtx && this.audioCtx.state === 'suspended') {
      await this.audioCtx.resume();
    }
  }

  // Waits for audio that has ALREADY been scheduled (via enqueueChunk) to
  // actually finish playing, without cutting it off and without tearing
  // down the AudioContext — so playback can resume immediately the next
  // time enqueueChunk is called (e.g. the next SPEAK narration after a
  // resume bridge).
  //
  // Use this at pause points the lesson can resume from (AWAIT_RESPONSE /
  // LEARNER_CHECKPOINT / LESSON_PAUSE). `stop()` used to be called at
  // these points instead, which does `audioCtx.close()` immediately —
  // that hard-cuts every buffer scheduled ahead of `currentTime` (the
  // deliberate lookahead buffer that keeps playback gapless), including
  // audio the learner hasn't actually heard yet. That's the frontend half
  // of the "voice gets cut off on AWAIT_RESPONSE" bug.
  async drain() {
    if (!this.audioCtx) return;
    const remaining = this.nextStartTime - this.audioCtx.currentTime;
    if (remaining > 0) {
      await new Promise(resolve => setTimeout(resolve, remaining * 1000));
    }
  }

  // True hard stop — cuts off audio immediately regardless of what's
  // scheduled. Only for actual teardown (leaving the lesson, unmounting,
  // or an explicit user-initiated stop). Never call this at a routine
  // pause point the lesson might resume from — use drain() there instead.
  stop() {
    if (this.audioCtx) {
      // Hard close the context to immediately cut off all scheduled audio
      this.audioCtx.close();
      this.audioCtx = null;
      this.nextStartTime = 0;
    }
  }

  close() {
    this.stop();
  }
}