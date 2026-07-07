import React, { useState, useRef, useEffect, useCallback } from 'react'
import katex from 'katex'

// ─────────────────────────────────────────────────────────────────────────────
// SlidingExplainBoard — Smart Education mid-lesson question board
//
// Core principle (from the product vision PDF):
//   A teacher CANNOT explain a learner's question while writing on the other
//   side of the board. When a student raises their hand the teacher STOPS,
//   turns around, pulls down a second board, works through the answer there,
//   then slides it back up and resumes exactly where they left off.
//
// Pause contract:
//   1. Learner submits question → triggerPause() freezes instruction loop
//   2. Explain board slides DOWN → fetches answer → writes with chalk-reveal
//   3. Learner presses RESUME LESSON → slide-UP animation begins
//   4. Animation fully ends → onResume() fires → instruction loop unblocks
//   The lesson NEVER resumes before the board is visually gone.
//
// ── Layout ───────────────────────────────────────────────────────────────────
//   ┌─────────────────────────────────────────────────────────────────────┐
//   │  Lesson board  ←── frozen, dimmed while explain board is over it   │
//   │  ┌───────────────────────────────────────────────────────────────┐  │
//   │  │  EXPLANATION BOARD  (position:absolute inset:0)               │  │
//   │  │  slides DOWN from above on open, UP on dismiss                │  │
//   │  │  ┌ top rail: ⏸ LESSON PAUSED · question echo · RESUME ↑ ┐   │  │
//   │  │  │ board surface: KaTeX + prose chalk-reveal               │   │  │
//   │  │  │ lumina strip: typewriter narration                      │   │  │
//   │  │  └ chalk tray ─────────────────────────────────────────────┘   │  │
//   │  └───────────────────────────────────────────────────────────────┘  │
//   │  Lesson resumes the instant slide-out animation ends                │
//   └─────────────────────────────────────────────────────────────────────┘
//
// ── Exports ───────────────────────────────────────────────────────────────────
//   default         SlidingExplainBoard
//   useLessonPause  Promise-based gate — wire into Lesson.jsx instruction loop
//   QuestionInput   Input bar that lives below the lesson board
//   renderLine      KaTeX renderer  (shared contract with Lesson.jsx)
//   renderTextLine  Prose renderer  (shared contract with Lesson.jsx)
// ─────────────────────────────────────────────────────────────────────────────

// ── Pacing ────────────────────────────────────────────────────────────────────
const SPEEDS = { Slow: 3500, Normal: 1800, Fast: 600 }

// ── Chalk-reveal easing — cubic ease-in-out, identical to Lesson.jsx ──────────
function revealLine(i, ms, setClipPcts, onDone) {
  let raf, start
  const tick = (ts) => {
    if (!start) start = ts
    const raw   = Math.min((ts - start) / ms, 1)
    const eased = raw < 0.5
      ? 4 * raw * raw * raw
      : 1 - Math.pow(-2 * raw + 2, 3) / 2
    setClipPcts(prev => {
      const next = [...prev]; next[i] = eased * 100; return next
    })
    if (raw < 1) { raf = requestAnimationFrame(tick) } else { onDone() }
  }
  raf = requestAnimationFrame(tick)
  return () => cancelAnimationFrame(raf)
}

// ── Renderers — exported so Lesson.jsx can import and share the same contracts ─
export function renderLine(latex) {
  try {
    return {
      html: katex.renderToString(latex, { throwOnError: true, displayMode: false, output: 'html' }),
      latex,
      renderType: 'latex',
    }
  } catch { return null }
}

function escapeHtml(v = '') {
  return String(v)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;')
}

export function renderTextLine(text, { isHeading = false } = {}) {
  const safe = escapeHtml(text).replace(/\n/g, '<br/>')
  return {
    html: isHeading
      ? `<span style="font-family:inherit;font-size:11px;font-weight:600;letter-spacing:0.12em;` +
        `text-transform:uppercase;color:rgba(99,200,255,0.65);display:block;` +
        `padding:12px 0 4px;text-align:center;">${safe}</span>`
      : `<div style="font-family:'Crimson Pro',Georgia,serif;font-size:18px;line-height:1.58;` +
        `font-weight:500;letter-spacing:0.01em;color:inherit;display:block;` +
        `max-width:min(820px,100%);text-align:left;white-space:normal;word-break:break-word;">${safe}</div>`,
    isText: true, isHeading, rawText: text, renderType: 'text',
  }
}

// ── splitIntoSentences ────────────────────────────────────────────────────────────
// Lesson.jsx board lines are KaTeX — white-space:nowrap, always one physical
// row — so the left-to-right clip sweeps a single line cleanly.
// Prose text from the answer engine is multi-sentence. Without splitting, one
// clipPath covers every wrapped row and all rows reveal simultaneously (the
// "multiple lines at once" effect). Splitting at sentence boundaries gives
// short single-row chunks so the horizontal clip matches the Lesson.jsx feel.
// Headings and KaTeX lines are returned as-is.
function splitIntoSentences(line) {
  if (!line.isText || line.isHeading) return [line]
  const raw = (line.rawText || '').trim()
  if (!raw) return [line]
  // Split after . ! ? followed by whitespace (won't break on 3.14 etc.)
  const parts = raw.split(/(?<=[.!?])\s+/).map(s => s.trim()).filter(Boolean)
  if (parts.length <= 1) return [line]
  return parts.map(s => renderTextLine(s))
}

// ── Lumina label colours — matches Lesson.jsx colour map exactly ───────────────
function luminaColors(label) {
  const map = {
    'COMMON ERROR':   { text: 'rgba(255,150,90,0.80)',  border: 'rgba(255,150,90,0.20)',  bg: 'rgba(255,150,90,0.04)'  },
    'WHY IT HAPPENS': { text: 'rgba(255,210,80,0.80)',  border: 'rgba(255,210,80,0.20)',  bg: 'rgba(255,210,80,0.04)'  },
    'CORRECTION':     { text: 'rgba(90,220,130,0.80)',  border: 'rgba(90,220,130,0.20)',  bg: 'rgba(90,220,130,0.04)'  },
    'NEXT UP':        { text: 'rgba(185,120,255,0.80)', border: 'rgba(185,120,255,0.20)', bg: 'rgba(185,120,255,0.04)' },
  }
  return map[label] || { text: 'rgba(99,200,255,0.80)', border: 'rgba(99,200,255,0.18)', bg: 'rgba(99,200,255,0.04)' }
}

// ─────────────────────────────────────────────────────────────────────────────
// useLessonPause
//
// A Promise-based gate that suspends the lesson instruction loop while the
// explanation board is open.  Uses refs so triggerPause / triggerResume are
// stable across renders and safe to call from async closures.
//
// ── Usage in Lesson.jsx ───────────────────────────────────────────────────────
//
//   const { pauseIfNeeded, triggerPause, triggerResume } = useLessonPause()
//
//   // 1. Wrap every step in the instruction loop:
//   for (const inst of allInstructions) {
//     await pauseIfNeeded()   // freezes here while explain board is open;
//                             // zero-cost (instant resolve) when not paused
//     if (inst.kind === 'board') await pushAndReveal(allLines[inst.idx], allLines.length)
//     else                       await showLuminaText(inst.text, inst.label)
//   }
//
//   // 2. When the learner submits a question:
//   triggerPause()            // freeze the loop at the next pauseIfNeeded()
//   setCurrentQuestion(q)
//   setExplainVisible(true)   // mount the explain board → slide-in begins
//
//   // 3. Wire to the board:
//   <SlidingExplainBoard
//     onResume={triggerResume}   // called after slide-out ends → unblocks loop
//     ...
//   />
// ─────────────────────────────────────────────────────────────────────────────
export function useLessonPause() {
  const resolveRef = useRef(null)   // holds the pending Promise resolver
  const pausedRef  = useRef(false)  // whether the loop is currently blocked

  // Called before each instruction step.
  // Returns immediately when not paused; blocks until triggerResume() when paused.
  const pauseIfNeeded = useCallback(() => {
    if (!pausedRef.current) return Promise.resolve()
    return new Promise(resolve => { resolveRef.current = resolve })
  }, [])

  // Called the moment the learner submits a question — freezes the loop.
  const triggerPause = useCallback(() => {
    pausedRef.current = true
  }, [])

  // Called AFTER the slide-out animation ends — this is when the teacher
  // "picks up the chalk again" and the lesson board resumes writing.
  const triggerResume = useCallback(() => {
    pausedRef.current = false
    const r = resolveRef.current
    resolveRef.current = null
    if (r) r()   // resolves the suspended pauseIfNeeded() Promise
  }, [])

  return { pauseIfNeeded, triggerPause, triggerResume }
}

// ─────────────────────────────────────────────────────────────────────────────
// SlidingExplainBoard
//
// Props:
//   visible       boolean               mount / unmount gate (parent controls)
//   question      string                the learner's question text
//   speedName     'Slow'|'Normal'|'Fast' shared pacing with main board
//   mode          { text: string }      chalk colour tokens from Lesson.jsx
//   onClose       fn()                  parent sets visible=false on call
//   onResume      fn()                  fired AFTER slide-out animation ends
//   onAskBackend  async fn(q) → EITHER
//                   { resumed: true }                    understanding CONFIRMED —
//                                                         parent is already closing
//                                                         the board; render nothing
//                 OR
//                   { intro?:      string                optional opening Lumina line
//                     lines:       renderedLine[]        board content
//                     narrations:  {text,label?}[] }     parallel to lines
// ─────────────────────────────────────────────────────────────────────────────
export default function SlidingExplainBoard({
  visible      = false,
  question     = '',
  speedName    = 'Normal',
  mode         = { text: '#e2f4ff' },
  onClose            = () => {},
  onResume           = () => {},
  // Optional SSE path: if a parent ever wires a GET /stream/explain SSE
  // endpoint, pass a fn(question) → EventSource here and the board will
  // drive itself from typed BOARD_LINE/TEACHER_SAYS events, same protocol
  // as the lesson board. Lesson.jsx currently does NOT pass this (routes.py
  // has no /stream/explain route yet), so the board always uses the
  // onAskBackend REST path below.
  onOpenExplainSSE   = null,
  // Primary path: REST round-trip to POST /answer/ask via Lesson.jsx's
  // handleAskBackend. Drives the full Q&A loop — initial answer, escalation,
  // probing, and CONFIRMED → resume.
  onAskBackend       = async () => ({ lines: [], narrations: [] }),
}) {
  // ── Slide lifecycle ────────────────────────────────────────────────────────
  // 'hidden' → 'sliding-in' → 'visible' → 'sliding-out' → 'hidden'
  // Stored in a ref AND state: ref is read inside animationend handler
  // (avoids stale-closure bug), state drives the animation CSS.
  const slideStateRef = useRef('hidden')
  const [slideState, _setSlideState] = useState('hidden')
  const setSlideState = (s) => { slideStateRef.current = s; _setSlideState(s) }

  const [mounted, setMounted] = useState(false)

  // ── Board writing ──────────────────────────────────────────────────────────
  const [lines,        setLines]        = useState([])
  const [visibleCount, setVisibleCount] = useState(0)
  const [clipPcts,     setClipPcts]     = useState([])
  const [writing,      setWriting]      = useState(false)
  const [done,         setDone]         = useState(false)
  const [loadError,    setLoadError]    = useState('')
  const [loading,      setLoading]      = useState(false)

  // ── Learner reply (follow-up Q&A turns) ───────────────────────────────────
  const [replyValue,   setReplyValue]   = useState('')
  const [replyLoading, setReplyLoading] = useState(false)
  const [replyError,   setReplyError]   = useState('')

  // ── Lumina narration ───────────────────────────────────────────────────────
  const [luminaText,   setLuminaText]   = useState('')
  const [luminaLabel,  setLuminaLabel]  = useState('LUMINA')
  const [luminaTyped,  setLuminaTyped]  = useState('')
  const [luminaTyping, setLuminaTyping] = useState(false)

  const boardRef      = useRef(null)
  const cleanupRef    = useRef([])
  const luminaTimer   = useRef(null)
  const speedRef      = useRef(speedName)
  const userScrolled  = useRef(false)
  const resumeFired   = useRef(false)   // guard: onResume fires at most once per open
  const esRef         = useRef(null)    // the explain board's own EventSource (SSE path)

  useEffect(() => { speedRef.current = speedName }, [speedName])

  // ── Inject keyframes once ──────────────────────────────────────────────────
  useEffect(() => {
    const id = 'seb-keyframes'
    if (document.getElementById(id)) return
    const s = document.createElement('style')
    s.id = id
    s.textContent = [
      // Board descends from above on entry, retracts back up on exit
      `@keyframes seb-slide-in  { from{transform:translateY(-106%);opacity:0.4;} to{transform:translateY(0);opacity:1;} }`,
      `@keyframes seb-slide-out { from{transform:translateY(0);opacity:1;} to{transform:translateY(-106%);opacity:0;} }`,
      // Utility animations
      `@keyframes seb-blink  { 0%,100%{opacity:0;} 50%{opacity:1;} }`,
      `@keyframes seb-dot    { 0%,80%,100%{opacity:0;} 40%{opacity:1;} }`,
      `@keyframes seb-fadein { from{opacity:0;transform:translateY(5px);} to{opacity:1;transform:none;} }`,
      `@keyframes seb-pulse  { 0%,100%{opacity:0.38;} 50%{opacity:1;} }`,
    ].join('\n')
    document.head.appendChild(s)
  }, [])

  // ── Mount / unmount tied to `visible` ─────────────────────────────────────
  useEffect(() => {
    if (visible && !mounted) {
      resumeFired.current = false
      setMounted(true)
      // Double rAF: first frame mounts the DOM node, second starts the animation
      requestAnimationFrame(() => requestAnimationFrame(() => setSlideState('sliding-in')))
    }
    if (!visible && mounted) {
      // Abort any in-flight writing immediately
      cleanupRef.current.forEach(fn => fn())
      if (luminaTimer.current) clearInterval(luminaTimer.current)
      setSlideState('sliding-out')
    }
  }, [visible]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── animationend handler ───────────────────────────────────────────────────
  // Reads slideStateRef (not state) to avoid the stale-closure problem where
  // the closure captures 'sliding-in' but by the time animationend fires the
  // state has already changed to 'visible'.
  const handleAnimEnd = useCallback((e) => {
    if (e.target !== e.currentTarget) return   // ignore child animations

    const current = slideStateRef.current

    if (current === 'sliding-in') {
      setSlideState('visible')
    } else if (current === 'sliding-out') {
      // Board is completely off-screen — NOW the lesson can resume
      setMounted(false)
      setSlideState('hidden')
      resetInternals()
      if (!resumeFired.current) {
        resumeFired.current = true
        onResume()   // resolves pauseIfNeeded() in the instruction loop
      }
    }
  }, [onResume]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Begin fetch once the board is fully in view ────────────────────────────
  useEffect(() => {
    if (slideState === 'visible' && question) startFetch(question)
  }, [slideState]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Cleanup on unmount ─────────────────────────────────────────────────────
  useEffect(() => () => {
    cleanupRef.current.forEach(fn => fn())
    if (luminaTimer.current) clearInterval(luminaTimer.current)
    if (esRef.current) { esRef.current.close(); esRef.current = null }
  }, [])

  // ── Auto-scroll board ──────────────────────────────────────────────────────
  useEffect(() => {
    const el = boardRef.current
    if (!el || userScrolled.current) return
    if (el.scrollHeight >= el.clientHeight * 0.7)
      el.scrollTop = el.scrollHeight - el.clientHeight
  }, [visibleCount, lines])

  // ── resetInternals ─────────────────────────────────────────────────────────
  function resetInternals() {
    if (esRef.current) { esRef.current.close(); esRef.current = null }
    cleanupRef.current.forEach(fn => fn()); cleanupRef.current = []
    if (luminaTimer.current) { clearInterval(luminaTimer.current); luminaTimer.current = null }
    setLines([]); setVisibleCount(0); setClipPcts([])
    setWriting(false); setDone(false); setLoading(false); setLoadError('')
    setLuminaText(''); setLuminaLabel('LUMINA'); setLuminaTyped(''); setLuminaTyping(false)
    setReplyValue(''); setReplyLoading(false); setReplyError('')
    userScrolled.current = false
  }

  // ── pushAndReveal — identical contract to Lesson.jsx ──────────────────────
  const pushAndReveal = (line) => new Promise(resolve => {
    setLines(prev => {
      const next = [...prev, line]
      setClipPcts(pcts => [...pcts, 0])
      const idx = next.length - 1
      setTimeout(() => {
        setVisibleCount(idx + 1)
        const cancel = revealLine(idx, SPEEDS[speedRef.current], setClipPcts, resolve)
        cleanupRef.current.push(cancel)
      }, 60)
      return next
    })
  })

  // ── showLumina — typewriter narration, awaitable ───────────────────────────
  const showLumina = (text, label) => new Promise(resolve => {
    if (luminaTimer.current) { clearInterval(luminaTimer.current); luminaTimer.current = null }
    setLuminaText(text); setLuminaLabel(label || 'LUMINA')
    setLuminaTyped(''); setLuminaTyping(true)
    let idx = 0
    const sp      = speedRef.current
    const charMs  = sp === 'Fast' ? 8 : sp === 'Slow' ? 42 : 22
    const pauseMs = sp === 'Fast' ? 400 : sp === 'Slow' ? 1600 : 900
    luminaTimer.current = setInterval(() => {
      idx++
      setLuminaTyped(text.slice(0, idx))
      if (idx >= text.length) {
        clearInterval(luminaTimer.current); luminaTimer.current = null
        setLuminaTyping(false)
        setTimeout(resolve, pauseMs)
      }
    }, charMs)
  })

  // ── openExplainSSE — event queue, mirrors openLessonSSE in Lesson.jsx ────────
  //
  // Handles the same typed events as the lesson stream so the explain board
  // and lesson board speak an identical protocol.  Any event not listed here
  // is silently ignored (zero-cost no-op), which is safe — the queue moves on.
  //
  // SEGMENT_END receives explicit handling (the same fix applied to Lesson.jsx):
  // without it the queue would resolve the event instantly, collapsing the
  // visual gap between explanation segments to zero.
  function openExplainSSE(es) {
    esRef.current = es
    let queue = Promise.resolve()

    es.onmessage = (evt) => {
      let data
      try { data = JSON.parse(evt.data) } catch { return }

      queue = queue.then(async () => {
        if (data.event === 'BOARD_HEADING') {
          const line = renderTextLine(data.payload.content, { isHeading: true })
          if (line) await pushAndReveal(line)
        }
        else if (data.event === 'BOARD_LINE') {
          const line = renderLine(data.payload.content)
          if (line) {
            await pushAndReveal(line)
          } else {
            // Unparseable as KaTeX — surface in Lumina rather than drop it
            setLuminaText(prev => prev + (prev ? ' ' : '') + data.payload.content)
          }
        }
        else if (data.event === 'BOARD_TEXT') {
          const line = renderTextLine(data.payload.content, { isHeading: false })
          if (line) {
            await pushAndReveal(line)
          } else {
            setLuminaText(prev => prev + (prev ? ' ' : '') + data.payload.content)
          }
        }
        else if (data.event === 'TEACHER_SAYS') {
          // Use showLumina (typewriter) rather than raw setState so the learner
          // sees the narration typed out — more readable in an explanation context
          // where they're reading carefully, unlike the fast lesson stream.
          await showLumina(data.payload.content, data.payload.label || 'LUMINA')
        }
        else if (data.event === 'STEP_PAUSE') {
          await new Promise(r => setTimeout(r, data.payload?.delay_ms || 500))
        }
        else if (data.event === 'SEGMENT_END') {
          // Without this handler SEGMENT_END resolves as a zero-cost no-op and
          // the next segment fires immediately — the same bug fixed in Lesson.jsx.
          // Clear the Lumina strip and hold for a beat so the learner registers
          // that one part of the explanation is done before new content appears.
          setLuminaText('')
          await new Promise(r => setTimeout(r, 900))
        }
        else if (data.event === 'EXPLAIN_COMPLETE' || data.event === 'LESSON_COMPLETE') {
          es.close(); esRef.current = null
          setWriting(false); setDone(true)
        }
        else if (data.event === 'ERROR') {
          es.close(); esRef.current = null
          setLoadError(data.payload?.message || 'Stream error in explanation.')
          setWriting(false)
        }
        // All other event types (SEGMENT_START, RESUME_BRIDGE, LEARNER_CHECKPOINT,
        // LESSON_PAUSE) are lesson-level signals that don't apply here and are
        // intentionally left as silent no-ops.
      }).catch(err => console.error('Explain board queue error:', err))
    }

    es.onerror = () => {
      es.close(); esRef.current = null
      setLoadError('Explanation stream connection lost.')
      setWriting(false)
    }
  }

  // ── writeLines — split prose into sentences then reveal sequentially ──────
  // Each sentence is a short single-row chunk, so the horizontal left-to-right
  // clip matches the Lesson.jsx single-line reveal on every text entry.
  async function writeLines(boardLines, nars) {
    for (let i = 0; i < boardLines.length; i++) {
      const chunks = splitIntoSentences(boardLines[i])
      for (const chunk of chunks) {
        await pushAndReveal(chunk)
      }
      const nar = nars[i]
      if (nar?.text) await showLumina(nar.text, nar.label || 'LUMINA')
    }
  }

  // ── startFetch — SSE-primary, batch JSON fallback ──────────────────────────
  async function startFetch(q) {
    resetInternals()
    setLoading(true)
    try {
      // ── SSE path ──────────────────────────────────────────────────────────
      // The parent calls onOpenExplainSSE(question) and returns a ready
      // EventSource. The board takes ownership from here (closes it on
      // unmount / reset). Content arrives as typed events through openExplainSSE.
      if (onOpenExplainSSE) {
        const es = await Promise.resolve(onOpenExplainSSE(q))
        if (es) {
          setLoading(false); setWriting(true)
          openExplainSSE(es)
          return
        }
      }

      // ── Batch JSON fallback ───────────────────────────────────────────────
      // Used when no SSE provider is wired (onOpenExplainSSE is null) or when
      // the parent returns null/undefined (e.g. no active session yet).
      const result = await onAskBackend(q)

      // Parent already confirmed understanding and is resuming the lesson
      // (visible has been flipped to false) — nothing to write here.
      if (result?.resumed) {
        setLoading(false)
        return
      }

      const {
        lines:      boardLines = [],
        narrations: nars       = [],
        intro                  = '',
      } = result || {}

      setLoading(false); setWriting(true)

      // Teacher acknowledges the question before touching the board
      if (intro) await showLumina(intro, 'LUMINA')

      await writeLines(boardLines, nars)

      setWriting(false); setDone(true)
    } catch (e) {
      setLoading(false); setWriting(false)
      setLoadError(e.message || 'Could not reach the backend.')
    }
  }

  // ── handleReply — drives follow-up turns through the Q&A loop ────────────
  //
  // Called when the learner submits a reply to the explanation shown on the
  // board. Delegates to onAskBackend (which is Lesson.jsx's handleAskBackend),
  // passing the learner's text. That function owns all state about
  // examples_given, approaches_used, etc. — this component is stateless about
  // the Q&A progression; it only renders what the parent returns.
  //
  // Two outcomes:
  //   • Understanding NOT yet confirmed → parent returns a new explanation
  //     ({ intro, lines, narrations }) → board clears and re-renders it.
  //   • Understanding CONFIRMED → parent returns { resumed: true } and has
  //     already called triggerResume() + openLessonSSE() + setExplainVisible(false)
  //     itself, which collapses the board via the visible=false prop. We just
  //     stop our spinner — no new content is written.
  async function handleReply() {
    const text = replyValue.trim()
    if (!text || replyLoading || writing) return

    setReplyValue('')
    setReplyError('')
    setReplyLoading(true)

    try {
      const result = await onAskBackend(text)

      // Parent signalled resume (confirmed understanding) — it has already
      // flipped visible=false, which starts the slide-out. Nothing to render.
      if (!result || result.resumed) {
        setReplyLoading(false)
        return
      }

      // New explanation to show — clear board content and re-render
      cleanupRef.current.forEach(fn => fn()); cleanupRef.current = []
      if (luminaTimer.current) { clearInterval(luminaTimer.current); luminaTimer.current = null }
      setLines([]); setVisibleCount(0); setClipPcts([])
      setLuminaText(''); setLuminaTyped(''); setLuminaTyping(false)
      setDone(false); setReplyLoading(false)
      setWriting(true)
      userScrolled.current = false

      const { intro = '', lines: boardLines = [], narrations: nars = [] } = result

      if (intro) await showLumina(intro, 'LUMINA')
      await writeLines(boardLines, nars)

      setWriting(false); setDone(true)
    } catch (e) {
      setReplyLoading(false)
      setReplyError(e.message || 'Could not reach the backend. Try again.')
    }
  }

  // ── handleDismiss — starts slide-out; lesson resumes AFTER animation ends ──
  // Intentionally does NOT call onResume() here. onResume() is only called in
  // handleAnimEnd once the board has physically left the screen.
  function handleDismiss() {
    cleanupRef.current.forEach(fn => fn())
    if (luminaTimer.current) { clearInterval(luminaTimer.current); luminaTimer.current = null }
    onClose()   // → parent sets visible=false → useEffect triggers slide-out
  }

  if (!mounted) return null

  const isIn  = slideState === 'sliding-in' || slideState === 'visible'
  const isOut = slideState === 'sliding-out'
  const lc    = luminaColors(luminaLabel)

  return (
    <div
      onAnimationEnd={handleAnimEnd}
      style={{
        position: 'absolute', inset: 0, zIndex: 20,
        borderRadius: 22,
        // Slightly cooler/deeper tint than lesson board — reads as a distinct surface
        background: 'linear-gradient(160deg, #0a1628 0%, #060c18 100%)',
        border: '1px solid rgba(99,200,255,0.22)',
        boxShadow: [
          '0 0 0 1px rgba(99,200,255,0.08)',
          '0 40px 100px rgba(0,0,0,0.80)',
          '0 8px 32px rgba(0,0,0,0.55)',
          '0 -16px 60px rgba(99,200,255,0.06)',
        ].join(', '),
        display: 'flex', flexDirection: 'column',
        overflow: 'hidden',
        transformOrigin: 'top center',
        animation: isIn
          ? 'seb-slide-in 0.52s cubic-bezier(0.22,1,0.36,1) forwards'
          : isOut
          ? 'seb-slide-out 0.42s cubic-bezier(0.55,0,1,0.45) forwards'
          : 'none',
      }}
    >

      {/* ── Top rail — wooden frame of a classroom pull-down board ────────── */}
      <div style={{
        height: 44, flexShrink: 0,
        background: 'linear-gradient(180deg, rgba(16,28,50,0.98) 0%, rgba(10,16,30,0.88) 100%)',
        borderBottom: '2px solid rgba(99,200,255,0.10)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 20px', position: 'relative', zIndex: 5,
      }}>

        {/* Left: identity + pause indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {/* Handle dots */}
          {['rgba(255,100,80,0.60)', 'rgba(255,200,60,0.50)', 'rgba(80,210,120,0.45)'].map((bg, i) => (
            <div key={i} style={{ width: 6, height: 6, borderRadius: '50%', background: bg, boxShadow: `0 0 8px ${bg}` }} />
          ))}
          <div style={{ width: 1, height: 16, background: 'rgba(99,200,255,0.1)', margin: '0 6px' }} />
          <span style={{
            fontSize: 10, fontFamily: '"DM Mono", monospace',
            letterSpacing: '0.15em', color: 'rgba(99,200,255,0.55)',
            textTransform: 'uppercase',
          }}>
            EXPLANATION BOARD
          </span>
          {/* ⏸ LESSON PAUSED pill — key visual signal to the learner */}
          <span style={{
            fontSize: 9, fontFamily: '"DM Mono", monospace', letterSpacing: '0.12em',
            padding: '3px 9px', borderRadius: 20,
            border: '1px solid rgba(255,210,60,0.28)',
            background: 'rgba(255,210,60,0.07)',
            color: 'rgba(255,210,60,0.75)',
            display: 'flex', alignItems: 'center', gap: 5,
          }}>
            <span style={{ fontSize: 8 }}>⏸</span> LESSON PAUSED
          </span>
        </div>

        {/* Centre: question echo */}
        {question && (
          <span style={{
            fontSize: 11, fontFamily: '"DM Mono", monospace',
            color: 'rgba(226,244,255,0.25)', letterSpacing: '0.03em',
            maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            position: 'absolute', left: '50%', transform: 'translateX(-50%)',
          }}>
            ↳ {question}
          </span>
        )}

        {/* Right: resume button — lit up once explanation is complete */}
        <button
          onClick={handleDismiss}
          title="Slide board back up and resume lesson"
          style={{
            background: done
              ? 'linear-gradient(135deg, rgba(99,200,255,0.14) 0%, rgba(120,80,255,0.10) 100%)'
              : 'none',
            border: `1px solid ${done ? 'rgba(99,200,255,0.32)' : 'rgba(226,244,255,0.10)'}`,
            borderRadius: 7,
            color: done ? '#63c8ff' : 'rgba(226,244,255,0.38)',
            cursor: 'pointer',
            padding: '5px 14px', fontSize: 11,
            fontFamily: '"DM Mono", monospace', letterSpacing: '0.09em',
            display: 'flex', alignItems: 'center', gap: 7,
            transition: 'all 0.22s ease',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.color = '#e2f4ff'
            e.currentTarget.style.borderColor = 'rgba(99,200,255,0.45)'
            e.currentTarget.style.background = 'rgba(99,200,255,0.09)'
          }}
          onMouseLeave={e => {
            e.currentTarget.style.color = done ? '#63c8ff' : 'rgba(226,244,255,0.38)'
            e.currentTarget.style.borderColor = done ? 'rgba(99,200,255,0.32)' : 'rgba(226,244,255,0.10)'
            e.currentTarget.style.background = done
              ? 'linear-gradient(135deg, rgba(99,200,255,0.14) 0%, rgba(120,80,255,0.10) 100%)'
              : 'none'
          }}
        >
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="18 15 12 9 6 15"/>
          </svg>
          RESUME LESSON
        </button>
      </div>

      {/* ── Decorative chalk ruled lines across the board ─────────────────── */}
      <div style={{ position: 'absolute', left: 0, right: 0, top: 44, pointerEvents: 'none', zIndex: 1 }}>
        <div style={{ height: 1, background: 'rgba(99,200,255,0.03)', marginTop: 40 }} />
        <div style={{ height: 1, background: 'rgba(99,200,255,0.025)', marginTop: 100 }} />
        <div style={{ height: 1, background: 'rgba(99,200,255,0.018)', marginTop: 160 }} />
      </div>

      {/* ── Main scrollable board surface ─────────────────────────────────── */}
      <div
        ref={boardRef}
        onScroll={() => {
          const el = boardRef.current; if (!el) return
          userScrolled.current = (el.scrollHeight - el.scrollTop - el.clientHeight) > 40
        }}
        style={{
          flex: 1, overflowY: 'auto',
          padding: '32px 48px',
          display: 'flex', flexDirection: 'column',
          justifyContent: 'flex-start', alignItems: 'flex-start',
          position: 'relative', zIndex: 2,
        }}
      >

        {/* Loading — teacher is thinking */}
        {loading && (
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center', gap: 20,
          }}>
            <div style={{ display: 'flex', gap: 9 }}>
              {[0, 1, 2].map(i => (
                <div key={i} style={{
                  width: 7, height: 7, borderRadius: '50%',
                  background: 'rgba(99,200,255,0.55)',
                  animation: `seb-dot 1.4s ease-in-out ${i * 0.18}s infinite`,
                }} />
              ))}
            </div>
            <div style={{
              fontSize: 11, fontFamily: '"DM Mono", monospace',
              letterSpacing: '0.18em', color: 'rgba(99,200,255,0.4)',
              textTransform: 'uppercase', animation: 'seb-pulse 2.2s ease-in-out infinite',
            }}>
              Preparing answer…
            </div>
          </div>
        )}

        {/* Error */}
        {loadError && !loading && (
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center', gap: 16,
          }}>
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="rgba(240,110,110,0.55)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <p style={{ margin: 0, fontSize: 13, fontFamily: '"Cabinet Grotesk", sans-serif', color: 'rgba(240,110,110,0.72)', textAlign: 'center', maxWidth: 280 }}>
              {loadError}
            </p>
            <button
              onClick={() => startFetch(question)}
              style={{
                background: 'none', border: '1px solid rgba(240,110,110,0.28)',
                color: 'rgba(240,110,110,0.65)', borderRadius: 8,
                padding: '6px 18px', fontSize: 12, cursor: 'pointer',
                fontFamily: '"DM Mono", monospace', letterSpacing: '0.09em',
              }}
            >
              RETRY
            </button>
          </div>
        )}

        {/* Idle — board just opened, fetch hasn't returned yet */}
        {/* Guard also excludes `writing` and `done` so a PROBE turn (empty   */}
        {/* lines, but done=true) doesn't flash the ghost "PREPARING ANSWER". */}
        {!loading && !loadError && !writing && !done && lines.length === 0 && (
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center',
            color: 'rgba(99,200,255,0.10)', fontFamily: '"DM Mono", monospace',
            fontSize: 12, letterSpacing: '0.22em', pointerEvents: 'none',
          }}>
            <span style={{ fontSize: 36, opacity: 0.3, marginBottom: 14 }}>⁑</span>
            PREPARING ANSWER
          </div>
        )}

        {/* Board lines — identical render contract to Lesson.jsx          */}
        {/* Gate widened: `writing || done` ensures the reply input, writing */}
        {/* indicator, and completion cue render even when `lines` is empty, */}
        {/* which happens on PROBE turns (no board content, only probe text). */}
        {(lines.length > 0 || writing || done) && (
          <div style={{
            display: 'flex', flexDirection: 'column',
            alignItems: 'flex-start', gap: 1,
            width: '100%', position: 'relative', zIndex: 2,
          }}>
            {lines.map((line, i) => {
              const pct       = clipPcts[i] ?? 0
              const isText    = !!line.isText
              const isHeading = !!line.isHeading
              return (
                <div key={i} style={{
                  opacity: i < visibleCount ? 1 : 0,
                  transition: 'opacity 0.25s ease',
                  width: '100%', display: 'flex', justifyContent: 'flex-start',
                }}>
                  <div
                    style={{
                      fontSize: 15,
                      color: mode.text || '#e2f4ff',
                      textShadow: `0 0 12px ${(mode.text || '#e2f4ff')}44`,
                      lineHeight: isText ? 1.58 : 0.2,
                      margin: 0,
                      padding: isText ? (isHeading ? '10px 0 2px' : '5px 0') : '5px 25px',
                      userSelect: isText ? 'text' : 'none',
                      display: isText ? 'block' : 'inline-block',
                      maxWidth: isText ? 'min(820px,100%)' : 'none',
                      width: isText ? '100%' : 'auto',
                      textAlign: 'left',
                      letterSpacing: isHeading ? '0.12em' : '0.01em',
                      fontWeight: isText && !isHeading ? 500 : undefined,
                      whiteSpace: isText ? 'normal' : 'nowrap',
                      wordBreak: 'break-word',
                      clipPath: `inset(0 ${100 - pct}% 0 0)`,
                    }}
                    dangerouslySetInnerHTML={{ __html: line.html }}
                  />
                </div>
              )
            })}

            {/* Writing indicator */}
            {writing && (
              <div style={{
                fontSize: 11, fontFamily: '"DM Mono", monospace',
                letterSpacing: '0.16em', color: 'rgba(99,200,255,0.5)',
                marginTop: 14, animation: 'seb-blink 1.2s ease-in-out infinite',
              }}>
                WRITING…
              </div>
            )}

            {/* Completion cue */}
            {done && (
              <div style={{
                marginTop: 18, fontSize: 10,
                fontFamily: '"DM Mono", monospace', letterSpacing: '0.14em',
                color: 'rgba(99,200,255,0.32)', lineHeight: 1.7,
                animation: 'seb-fadein 0.5s ease-out forwards',
              }}>
                ✓ EXPLANATION COMPLETE<br/>
                <span style={{ opacity: 0.6 }}>Still confused? Reply below — or press RESUME LESSON ↑ to continue.</span>
              </div>
            )}

            {/* ── Learner reply input — appears once explanation is done ─── */}
            {done && (
              <div style={{
                marginTop: 24, width: '100%',
                animation: 'seb-fadein 0.45s 0.15s ease-out both',
              }}>
                {/* Divider */}
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14,
                }}>
                  <div style={{ flex: 1, height: 1, background: 'rgba(99,200,255,0.08)' }} />
                  <span style={{
                    fontSize: 9, fontFamily: '"DM Mono", monospace',
                    letterSpacing: '0.18em', color: 'rgba(99,200,255,0.25)',
                    textTransform: 'uppercase', whiteSpace: 'nowrap',
                  }}>
                    Still have questions?
                  </span>
                  <div style={{ flex: 1, height: 1, background: 'rgba(99,200,255,0.08)' }} />
                </div>

                {/* Reply input row */}
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '10px 14px',
                  background: replyLoading ? 'rgba(7,11,20,0.5)' : 'rgba(10,18,32,0.75)',
                  border: `1px solid ${replyError ? 'rgba(240,110,110,0.30)' : 'rgba(99,200,255,0.16)'}`,
                  borderRadius: 12,
                  transition: 'border-color 0.2s ease, background 0.2s ease',
                }}>
                  {/* Question mark icon */}
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
                    stroke={replyLoading ? 'rgba(99,200,255,0.25)' : 'rgba(99,200,255,0.45)'}
                    strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                    style={{ flexShrink: 0 }}>
                    <circle cx="12" cy="12" r="10"/>
                    <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
                    <line x1="12" y1="17" x2="12.01" y2="17"/>
                  </svg>

                  <input
                    type="text"
                    placeholder={replyLoading ? 'Lumina is thinking…' : "I'm still confused about…"}
                    value={replyValue}
                    disabled={replyLoading}
                    onChange={e => { setReplyValue(e.target.value); if (replyError) setReplyError('') }}
                    onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleReply() } }}
                    style={{
                      flex: 1, background: 'none', border: 'none', outline: 'none',
                      color: replyLoading ? 'rgba(226,244,255,0.35)' : '#e2f4ff',
                      fontFamily: '"Cabinet Grotesk", sans-serif',
                      fontSize: 13, letterSpacing: '0.01em', caretColor: '#63c8ff',
                      transition: 'color 0.2s ease',
                    }}
                  />

                  <button
                    onClick={handleReply}
                    disabled={replyLoading || !replyValue.trim()}
                    style={{
                      background: (!replyLoading && replyValue.trim())
                        ? 'linear-gradient(135deg, rgba(99,200,255,0.14) 0%, rgba(120,80,255,0.09) 100%)'
                        : 'rgba(255,255,255,0.02)',
                      border: '1px solid',
                      borderColor: (!replyLoading && replyValue.trim())
                        ? 'rgba(99,200,255,0.35)'
                        : 'rgba(226,244,255,0.07)',
                      borderRadius: 8,
                      color: (!replyLoading && replyValue.trim())
                        ? '#63c8ff'
                        : 'rgba(226,244,255,0.2)',
                      padding: '5px 14px', fontSize: 11,
                      fontFamily: '"DM Mono", monospace', letterSpacing: '0.1em',
                      cursor: (!replyLoading && replyValue.trim()) ? 'pointer' : 'not-allowed',
                      transition: 'all 0.2s ease', whiteSpace: 'nowrap', flexShrink: 0,
                      display: 'flex', alignItems: 'center', gap: 6,
                    }}
                  >
                    {replyLoading ? (
                      <>
                        {[0, 1, 2].map(i => (
                          <span key={i} style={{
                            width: 3, height: 3, borderRadius: '50%',
                            background: 'rgba(99,200,255,0.5)', display: 'inline-block',
                            animation: `seb-dot 1.4s ease-in-out ${i * 0.18}s infinite`,
                          }} />
                        ))}
                      </>
                    ) : 'ASK →'}
                  </button>
                </div>

                {/* Inline error */}
                {replyError && (
                  <p style={{
                    margin: '8px 0 0', fontSize: 11,
                    fontFamily: '"DM Mono", monospace', letterSpacing: '0.08em',
                    color: 'rgba(240,110,110,0.70)',
                    animation: 'seb-fadein 0.25s ease-out',
                  }}>
                    ⚠ {replyError}
                  </p>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Lumina narration strip — pinned above chalk tray ──────────────── */}
      {luminaText && (
        <div style={{
          flexShrink: 0,
          borderTop: `1px solid ${lc.border}`,
          padding: '11px 20px',
          background: lc.bg,
          display: 'flex', alignItems: 'flex-start', gap: 12,
          transition: 'background 0.35s ease, border-color 0.35s ease',
          animation: 'seb-fadein 0.3s ease-out',
          position: 'relative', zIndex: 5,
        }}>
          <span style={{
            fontSize: 10, fontWeight: 700,
            color: lc.text, letterSpacing: '0.15em',
            flexShrink: 0, paddingTop: 3,
            textTransform: 'uppercase', fontFamily: '"DM Mono", monospace',
            transition: 'color 0.35s ease',
          }}>
            {luminaLabel}
          </span>
          <p style={{
            margin: 0,
            fontFamily: "'Crimson Pro', Georgia, serif",
            fontSize: 15, lineHeight: 1.65,
            color: 'rgba(226,244,255,0.78)',
            letterSpacing: '0.012em',
            flex: 1, minHeight: '1.65em',
          }}>
            {luminaTyped}
            {luminaTyping && (
              <span style={{
                display: 'inline-block', width: 1.5, height: '0.9em',
                background: lc.text, verticalAlign: 'text-bottom',
                marginLeft: 2, borderRadius: 1,
                animation: 'seb-blink 0.75s ease-in-out infinite alternate',
              }} />
            )}
          </p>
        </div>
      )}

      {/* ── Bottom chalk tray ─────────────────────────────────────────────── */}
      <div style={{
        height: 10, flexShrink: 0,
        background: 'linear-gradient(180deg, rgba(10,18,32,0.5) 0%, rgba(6,10,20,0.94) 100%)',
        borderTop: '1px solid rgba(99,200,255,0.07)',
        position: 'relative',
      }}>
        <div style={{
          position: 'absolute', inset: '2px 28px',
          backgroundImage: 'radial-gradient(circle, rgba(226,244,255,0.055) 1px, transparent 1px)',
          backgroundSize: '14px 5px',
        }} />
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// QuestionInput
//
// The question bar below the lesson board. Visible whenever the lesson is
// playing or done. Disabled (but still shown) while the explain board is open
// so the learner can't stack questions — and so they can see the lesson is
// paused.
//
// Props:
//   visible   boolean  — show only during/after a lesson
//   disabled  boolean  — true while explain board is open
//   onAsk     fn(q)    — called with the trimmed question string
// ─────────────────────────────────────────────────────────────────────────────
export function QuestionInput({ visible = false, disabled = false, onAsk = () => {} }) {
  const [value, setValue] = useState('')

  if (!visible) return null

  const submit = () => {
    const q = value.trim()
    if (!q || disabled) return
    onAsk(q)
    setValue('')
  }

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '10px 14px',
      background: disabled ? 'rgba(7,11,20,0.65)' : 'rgba(7,11,20,0.80)',
      border: `1px solid ${disabled ? 'rgba(255,210,60,0.15)' : 'rgba(99,200,255,0.14)'}`,
      borderRadius: 14,
      backdropFilter: 'blur(14px)', WebkitBackdropFilter: 'blur(14px)',
      opacity: disabled ? 0.5 : 1,
      transition: 'opacity 0.3s ease, border-color 0.3s ease, background 0.3s ease',
      animation: 'seb-fadein 0.3s ease-out',
    }}>
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
        stroke={disabled ? 'rgba(255,210,60,0.4)' : 'rgba(99,200,255,0.5)'}
        strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
        <line x1="12" y1="17" x2="12.01" y2="17"/>
      </svg>

      <input
        type="text"
        placeholder={disabled ? 'Lesson paused — reading explanation…' : 'Ask a question about this step…'}
        value={value}
        onChange={e => setValue(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }}
        disabled={disabled}
        style={{
          flex: 1, background: 'none', border: 'none', outline: 'none',
          color: '#e2f4ff', fontFamily: '"Cabinet Grotesk", sans-serif',
          fontSize: 13, letterSpacing: '0.01em', caretColor: '#63c8ff',
        }}
      />

      <button
        onClick={submit}
        disabled={disabled || !value.trim()}
        style={{
          background: (!disabled && value.trim())
            ? 'linear-gradient(135deg, rgba(99,200,255,0.16) 0%, rgba(120,80,255,0.11) 100%)'
            : 'rgba(255,255,255,0.025)',
          border: '1px solid',
          borderColor: (!disabled && value.trim()) ? 'rgba(99,200,255,0.38)' : 'rgba(226,244,255,0.07)',
          borderRadius: 8,
          color: (!disabled && value.trim()) ? '#63c8ff' : 'rgba(226,244,255,0.2)',
          padding: '5px 14px', fontSize: 11,
          fontFamily: '"DM Mono", monospace', letterSpacing: '0.1em',
          cursor: (!disabled && value.trim()) ? 'pointer' : 'not-allowed',
          transition: 'all 0.22s ease', whiteSpace: 'nowrap',
        }}
      >
        ASK →
      </button>
    </div>
  )
}