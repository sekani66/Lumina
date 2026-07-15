import React, { useState, useRef, useEffect } from 'react'

import '../styles/authStyles.css'
import { S, LOADING_STAGES, EXPLAIN_STYLES as ES } from '../styles/lessonPageStyles'
import { PARTICLES } from '../constants/floatingParticles'
import '../styles/lessonPage.css'

import { PRESETS, SPEEDS, SSE_DELAYS, MODES, LESSON_OPTIONS } from '../constants/lessoPageConstants'

import { getLuminaTheme } from '../utils/luminaThemes'
import { parseLatexLines, revealLine, renderLine, renderTextLine } from '../utils/boardAnimations'
import { PCMAudioPlayer } from '../utils/pcmAudioPlayer'
import { useLessonPause } from '../utils/lessonPause'


const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'


// ════════════════════════════════════════════════════════════════════════════
// COMPONENT
// ════════════════════════════════════════════════════════════════════════════

export default function LessonPage({ onBack, courseData }) {
  const modeName = 'Chalk'
  const [speedName,   setSpeedName]   = useState('Slow')
  const [customLatex, setCustomLatex] = useState('')
  const [error,       setError]       = useState('')
  // retryAction holds a zero-arg function to re-run whatever just failed, or
  // null if the current error isn't retryable (e.g. plain validation errors).
  // Read by the error banner's "Retry" button — see showError/clearError below.
  const [retryAction, setRetryAction] = useState(null)
  const [playing,     setPlaying]     = useState(false)
  const [done,        setDone]        = useState(false)
  const [progress,    setProgress]    = useState(0)
  const [openChapter, setOpenChapter] = useState(null)
  const [completedLessons, setCompletedLessons] = useState(new Set([-1]))
  const [backendOk,   setBackendOk]   = useState(null)

  // ── Lesson / Stream State ────────────────────────────────────────────────
  const [loadingStage,    setLoadingStage]    = useState(null)
  const [currentLesson,   setCurrentLesson]   = useState(null)
  const [sessionId,       setSessionId]       = useState(null)
  const [teachingScript,  setTeachingScript]  = useState(null)
  const [questionBank,    setQuestionBank]    = useState(null)
  const [activeSegment,   setActiveSegment]   = useState(null)

  // Refs for callbacks
  const currentLessonRef = useRef(null)
  const totalSegmentsRef = useRef(0)
  const sessionIdRef     = useRef(null)

  // ── Q&A Engine State ─────────────────────────────────────────────────────
  const [qaState, setQaState] = useState({
    examplesGiven:        0,
    previousApproach:     null,
    approachesUsed:       [],
    conversationHistory:  [],
    probeQuestion:        null,   // last probe sent to learner; echoed back on Turn 2+
    awaitingProbeResponse: false, // true after PROBE fires; next learner input → confusion_location
    awaitingFinalConfirmation: false, // true after the soft "does that make sense" check fires;
                                       // MUST be echoed back or the reply gets misread as a fresh
                                       // probe answer and the check loops forever
    boardState: [],
    coreExplanation: null, // one-line summary of the last substantive explanation given this
                            // Q&A thread; echoed back to /answer/ask like probeQuestion, and
                            // used (instead of probeQuestion) to build the resume bridge's
                            // answer_summary so the bridge isn't contextless
  })

  // ── AI ask (sidebar helper) ──────────────────────────────────────────────
  const [aiPrompt,            setAiPrompt]            = useState('')
  const [aiLoading,           setAiLoading]           = useState(false)
  const [aiError,             setAiError]             = useState('')
  const [aiExplanation,       setAiExplanation]       = useState([])
  const [visibleExplanations, setVisibleExplanations] = useState(0)

  // ── Section label (drives practice-box color theme via getLuminaTheme) ───
  const [luminaLabel, setLuminaLabel] = useState('LUMINA')

  // ── Explain board (mid-lesson questions) ────────────────────────────────
  const [explainVisible,     setExplainVisible]     = useState(false)
  const [currentQuestion,    setCurrentQuestion]    = useState('')
  const [isAwaitingPractice, setIsAwaitingPractice] = useState(false)
  const [practiceInput,      setPracticeInput]      = useState('')
  // Holds the AWAIT_RESPONSE prompt text (e.g. "Which number is the slope,
  // and which is the y-intercept?") so it can be shown as the placeholder
  // on the practice-answer input below — this is the only TEACHER_SAYS-
  // adjacent content still surfaced to the learner now that the narration
  // panel has been removed.
  const [practicePrompt,     setPracticePrompt]     = useState('')
  const { triggerResume } = useLessonPause()

  // ── Raised hand (mirrors backend streaming_engine.py hand-raise flow) ────
  // 'idle'         — not raised.
  // 'raised'       — learner tapped it; POST sent, waiting for the backend
  //                  to notice (HAND_RAISE_ACK).
  // 'acknowledged' — backend noted it (HAND_RAISE_ACK received) but the
  //                  teacher is still finishing the current step.
  // 'active'       — teacher has spoken the acknowledgement line and
  //                  paused (LESSON_PAUSE, raised_as_hand: true) — the
  //                  learner may now type their question.
  const [handState,         setHandState]         = useState('idle')
  const [handQuestionInput, setHandQuestionInput] = useState('')
  // True from the moment the learner taps to lower their hand until the
  // next LESSON_PAUSE(raised_as_hand) has been consumed. Covers the window
  // where the backend already committed to pausing for the hand-raise
  // (mid-sentence, before it can re-check) but the learner cancelled in
  // the meantime — see handleRaiseHand / LESSON_PAUSE handler below.
  const handLowerRequestedRef = useRef(false)

  const explanationRef = useRef(null)
  const boardRef       = useRef(null)
  const userScrolled   = useRef(false)

  const [sourceMode,   setSourceMode]   = useState('preset')
  const [lines,        setLines]        = useState([])
  const [lineContents, setLineContents] = useState([])
  const [boardAnnotations, setBoardAnnotations] = useState({})
  const [visibleCount, setVisibleCount] = useState(0)
  const [clipPcts,     setClipPcts]     = useState([])

  // ── Right board (Q&A / Explanation panel) state ──────────────────────────
  const [explainLines,        setExplainLines]        = useState([])
  const [explainLineContents, setExplainLineContents] = useState([])
  // explainLineIds: unique id per board line, parallel to explainLineContents.
  // Annotations are keyed by this id (not by text) so two lines that happen
  // to contain the same equation/string — e.g. "f(x) = ax^2 + bx + c" shown
  // again in a later, unrelated answer — don't share highlight state.
  const [explainLineIds,      setExplainLineIds]      = useState([])
  const [explainAnnotations,  setExplainAnnotations]  = useState({})
  const [explainVisibleCount, setExplainVisibleCount] = useState(0)
  const [explainClipPcts,     setExplainClipPcts]     = useState([])
  const [explainInput,        setExplainInput]        = useState('')
  const [explainLoading,      setExplainLoading]      = useState(false)
  // Holds the answer-stream's AWAIT_RESPONSE probe text (e.g. "What is 12
  // minus 5?"), shown as the placeholder on the Q&A follow-up input below
  // once LEARNER_CHECKPOINT fires — mirrors practicePrompt on the left.
  const [explainPrompt,       setExplainPrompt]       = useState('')

  // ── Left board refs ───────────────────────────────────────────────────────
  const cleanupRef          = useRef([])
  const esRef               = useRef(null)    // lesson SSE connection
  const writeIndexRef       = useRef(-1)
  const writeBufferRef      = useRef('')
  const lineContentsRef     = useRef([])
  const boardAnnotationsRef = useRef({})

  // Teacher voice — one PCMAudioPlayer instance for the whole session, fed
  // by TEACHER_AUDIO_CHUNK events from both the lesson SSE and answer SSE
  // (same underlying voice_engine clock either way). Lazily created so the
  // AudioContext is only constructed once a user gesture is available to
  // unlock it (see pcmAudioPlayer.js).
  const audioPlayerRef = useRef(null)
  const getAudioPlayer = () => {
    if (!audioPlayerRef.current) audioPlayerRef.current = new PCMAudioPlayer()
    return audioPlayerRef.current
  }

  // ── Pause / resume (board + voice) ────────────────────────────────────────
  // pausedRef gates the SSE processing queues for BOTH boards: every event
  // handler (lesson SSE and answer SSE) awaits waitIfPaused() as its very
  // first step, so once the in-flight event finishes, nothing further is
  // written to either board and no further audio chunks are enqueued until
  // resumeAll() runs. Already-buffered/playing audio is silenced directly
  // via the player so pausing takes effect immediately, not just once the
  // buffer drains.
  const pausedRef        = useRef(false)
  const resumeWaitersRef = useRef([])
  const [boardPaused, setBoardPaused] = useState(false)

  const waitIfPaused = () => {
    if (!pausedRef.current) return Promise.resolve()
    return new Promise(resolve => { resumeWaitersRef.current.push(resolve) })
  }

  const handleTogglePause = async () => {
    const player = getAudioPlayer()
    if (!pausedRef.current) {
      pausedRef.current = true
      setBoardPaused(true)
      // Suspends the AudioContext clock — silences whatever's already
      // playing immediately. New chunks won't be enqueued anyway since
      // the SSE queues are gated on waitIfPaused() above.
      await player.pause()
    } else {
      // Resume the audio clock first, then release the board — so the
      // very next line/chunk the board writes lines up with audio that's
      // actually flowing again, not a still-frozen context.
      await player.resume()
      pausedRef.current = false
      setBoardPaused(false)
      const waiters = resumeWaitersRef.current
      resumeWaitersRef.current = []
      waiters.forEach(fn => fn())
    }
  }

  // ── Right board refs ──────────────────────────────────────────────────────
  const answerEsRef            = useRef(null) // answer SSE connection (separate from lesson SSE)
  const explainBoardRef        = useRef(null)
  const explainLineContentsRef = useRef([])
  const explainLineIdsRef      = useRef([])   // unique per-line ids, parallel to explainLineContentsRef
  const explainLineIdCounterRef = useRef(0)   // monotonic counter — never reused, even across erases
  const explainCleanupRef      = useRef([])
  const explainUserScrolled    = useRef(false)
  const explainWriteIndexRef   = useRef(-1)   // in-progress BOARD_WRITE_START/APPEND line index
  const explainWriteBufferRef  = useRef('')   // accumulated raw chars for the in-progress right-board WRITE

  const escapeHtml = (s) => String(s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

  // ── findLineIndexForTarget — left board ───────────────────────────────────
  const findLineIndexForTarget = (target) => {
    const needle = String(target || '').replace(/\s+/g, '').toLowerCase()
    if (!needle) return -1
    const contents = lineContentsRef.current
    for (let i = contents.length - 1; i >= 0; i--) {
      const hay = String(contents[i] || '').replace(/\s+/g, '').toLowerCase()
      if (hay && hay.includes(needle)) return i
    }
    return -1
  }

  // ── findExplainLineIndexForTarget — right board ───────────────────────────
  // Mirror of findLineIndexForTarget but searches explainLineContentsRef,
  // used by BOARD_HIGHLIGHT/UNDERLINE/CIRCLE/ERASE events from the answer SSE.
  const findExplainLineIndexForTarget = (target) => {
    const needle = String(target || '').replace(/\s+/g, '').toLowerCase()
    if (!needle) return -1
    const contents = explainLineContentsRef.current
    for (let i = contents.length - 1; i >= 0; i--) {
      const hay = String(contents[i] || '').replace(/\s+/g, '').toLowerCase()
      if (hay && hay.includes(needle)) return i
    }
    return -1
  }

  const mode     = MODES[modeName]
  const duration = SPEEDS[speedName]

  useEffect(() => { currentLessonRef.current = currentLesson }, [currentLesson])
  useEffect(() => { sessionIdRef.current = sessionId }, [sessionId])

  // ── Auto-scroll explanation panel ────────────────────────────────────────
  useEffect(() => {
    if (explanationRef.current)
      explanationRef.current.scrollTop = explanationRef.current.scrollHeight
  }, [visibleExplanations, aiExplanation])

  // ── Auto-scroll left board ────────────────────────────────────────────────
  useEffect(() => {
    const el = boardRef.current
    if (!el || userScrolled.current) return
    if (el.scrollHeight >= el.clientHeight * 0.7)
      el.scrollTop = el.scrollHeight - el.clientHeight
  }, [visibleCount, lines])

  // ── Auto-scroll right board ───────────────────────────────────────────────
  useEffect(() => {
    const el = explainBoardRef.current
    if (!el || explainUserScrolled.current) return
    if (el.scrollHeight >= el.clientHeight * 0.7)
      el.scrollTop = el.scrollHeight - el.clientHeight
  }, [explainVisibleCount, explainLines])

  // ── Backend health check ──────────────────────────────────────────────────
  useEffect(() => {
    fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(2000) })
      .then(r => r.ok ? setBackendOk(true) : setBackendOk(false))
      .catch(() => setBackendOk(false))
  }, [])

  // ── Auto-trigger right-board Q&A when lesson pauses for a question ────────
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!explainVisible || !currentQuestion) return
    if (qaState.conversationHistory.length > 0) return
    handleExplainQuestion(currentQuestion)
  }, [explainVisible])

  // ── Cleanup ───────────────────────────────────────────────────────────────
  useEffect(() => {
    return () => {
      cleanupRef.current.forEach(fn => fn())
      if (esRef.current) esRef.current.close()
      if (answerEsRef.current) answerEsRef.current.close()
      if (audioPlayerRef.current) audioPlayerRef.current.close()
    }
  }, [])

  // ── pushAndReveal — left board ────────────────────────────────────────────
  const pushAndReveal = (line, totalKnown, raw = '') => new Promise(resolve => {
    lineContentsRef.current = [...lineContentsRef.current, raw]
    setLineContents(lineContentsRef.current)
    const idx = lineContentsRef.current.length - 1
    setLines(prev => [...prev, line])
    setClipPcts(prev => [...prev, 0])
    setTimeout(() => {
      setVisibleCount(idx + 1)
      if (sourceMode !== 'lesson') setVisibleExplanations(idx + 1)
      if (totalKnown) setProgress(Math.round(((idx + 1) / totalKnown) * 100))
      const cancel = revealLine(idx, duration, setClipPcts, resolve)
      cleanupRef.current.push(cancel)
    }, 60)
  })

  // ── pushAndRevealRight — right board ─────────────────────────────────────
  // Mirror of pushAndReveal for the Q&A board. Uses independent state/refs
  // so both boards animate and scroll in isolation.
  const pushAndRevealRight = (line, raw = '') => new Promise(resolve => {
    const newId = explainLineIdCounterRef.current++
    explainLineContentsRef.current = [...explainLineContentsRef.current, raw]
    explainLineIdsRef.current      = [...explainLineIdsRef.current, newId]
    setExplainLineContents([...explainLineContentsRef.current])
    setExplainLineIds([...explainLineIdsRef.current])
    const idx = explainLineContentsRef.current.length - 1
    setExplainLines(prev => [...prev, line])
    setExplainClipPcts(prev => [...prev, 0])
    setTimeout(() => {
      setExplainVisibleCount(idx + 1)
      const cancel = revealLine(idx, duration, setExplainClipPcts, resolve)
      explainCleanupRef.current.push(cancel)
    }, 60)
  })

  // ── pushExplainDivider — right board ──────────────────────────────────────
  // Marks the start of a new question in the running Q&A notes. Pushed once
  // per fresh question (not on follow-up turns within the same Q&A) so the
  // right board reads like a notebook: each explanation appended below the
  // last, clearly labeled, instead of the board being wiped between turns.
  const pushExplainDivider = (question) => {
    const idx = explainLineContentsRef.current.length
    const newId = explainLineIdCounterRef.current++
    explainLineContentsRef.current = [...explainLineContentsRef.current, '']
    explainLineIdsRef.current      = [...explainLineIdsRef.current, newId]
    setExplainLineContents([...explainLineContentsRef.current])
    setExplainLineIds([...explainLineIdsRef.current])
    setExplainLines(prev => [...prev, { kind: 'divider', question }])
    setExplainClipPcts(prev => [...prev, 100])
    setExplainVisibleCount(prev => Math.max(prev, idx + 1))
  }

  // ── finishExplainTurn — close out the current Q&A turn ───────────────────
  // Closes the answer SSE connection and clears in-flight write/loading
  // state, but deliberately leaves everything already written on the right
  // board in place. Explanations should stack up like notes so they stay
  // there to compare against the lesson — use this instead of
  // resetExplainBoard whenever a turn simply ends (confirmed or dismissed).
  const finishExplainTurn = () => {
    if (answerEsRef.current) { answerEsRef.current.close(); answerEsRef.current = null }
    explainCleanupRef.current.forEach(fn => fn())
    explainCleanupRef.current     = []
    explainWriteIndexRef.current  = -1
    explainWriteBufferRef.current = ''
    setExplainLoading(false)
    setExplainInput('')
    setExplainPrompt('')
  }

  // ── resetExplainBoard ─────────────────────────────────────────────────────
  // Full wipe of the right board — only for starting an entirely new lesson,
  // where the previous lesson's Q&A notes no longer apply.
  const resetExplainBoard = () => {
    finishExplainTurn()
    setExplainLines([])
    setExplainLineContents([])
    setExplainLineIds([])
    setExplainAnnotations({})
    explainLineContentsRef.current = []
    explainLineIdsRef.current      = []
    setExplainVisibleCount(0)
    setExplainClipPcts([])
    explainUserScrolled.current = false
    if (explainBoardRef.current) explainBoardRef.current.scrollTop = 0
  }

  // ── showError / clearError ────────────────────────────────────────────────
  // Central place to surface a failure to the learner. Any code path that
  // used to silently console.error/warn a fetch or SSE failure should call
  // showError instead, optionally with a zero-arg retry callback that redoes
  // whatever just failed. Rendered by the error banner in the JSX below.
  const showError = (message, retry = null) => {
    setError(message)
    setRetryAction(() => retry)
  }
  const clearError = () => {
    setError('')
    setRetryAction(null)
  }

  // ── resetBoard ────────────────────────────────────────────────────────────
  const resetBoard = () => {
    cleanupRef.current.forEach(fn => fn())
    cleanupRef.current = []
    if (esRef.current) { esRef.current.close(); esRef.current = null }
    setLuminaLabel('LUMINA')
    setLines([])
    setLineContents([])
    setBoardAnnotations({})
    lineContentsRef.current     = []
    boardAnnotationsRef.current = {}
    writeIndexRef.current  = -1
    writeBufferRef.current = ''
    setVisibleCount(0)
    setClipPcts([])
    setProgress(0)
    setDone(false)
    setPlaying(false)
    setLoadingStage(null)
    clearError()
    setVisibleExplanations(0)
    setIsAwaitingPractice(false)
    setPracticeInput('')
    setPracticePrompt('')
    setHandState('idle')
    setHandQuestionInput('')
    setQaState({
      examplesGiven: 0, previousApproach: null, approachesUsed: [],
      conversationHistory: [], probeQuestion: null, awaitingProbeResponse: false,
      awaitingFinalConfirmation: false, boardState: [], coreExplanation: null,
    })
    userScrolled.current = false
    if (boardRef.current) boardRef.current.scrollTop = 0
    resetExplainBoard()
    setExplainVisible(false)
  }

  // ── openLessonSSE ─────────────────────────────────────────────────────────
  const resumeInFlightRef = useRef(false)

  const openLessonSSE = (sid, isResume = false, resumeSummary = null) => {
    if (isResume) {
      if (resumeInFlightRef.current) {
        console.warn(`Ignored duplicate resume call for session ${sid} — a resume is already in flight.`)
        return
      }
      resumeInFlightRef.current = true
    }

    let url = `${API_BASE}/stream/${isResume ? 'resume' : 'lesson'}?session_id=${sid}`
    if (isResume && resumeSummary) {
      url += `&answer_summary=${encodeURIComponent(JSON.stringify(resumeSummary))}`
    }

    const es = new EventSource(url)
    esRef.current = es
    getAudioPlayer().ensureContext()
    let queue = Promise.resolve()

    es.onmessage = (evt) => {
      let data
      try { data = JSON.parse(evt.data) } catch (e) { return }

      queue = queue.then(async () => {
        await waitIfPaused()
        if (data.event === 'SECTION_START') {
          setActiveSegment(data.payload)
          const TYPE_LABEL = {
            INTRODUCTION: 'LUMINA', PREREQUISITE_REVIEW: 'LUMINA',
            CONCEPT_INTRODUCTION: 'LUMINA', WORKED_EXAMPLE: 'LUMINA',
            GUIDED_PRACTICE: 'PRACTICE', INDEPENDENT_PRACTICE: 'PRACTICE',
            CHALLENGE: 'PRACTICE', SUMMARY: 'LUMINA',
          }
          setLuminaLabel(TYPE_LABEL[data.payload?.section_type] ?? 'LUMINA')
          if (totalSegmentsRef.current) {
            setProgress(Math.round(((data.payload?.section_index + 1) / totalSegmentsRef.current) * 100))
          }
        }
        else if (data.event === 'SECTION_END') {
          // Insert a blank row so the next section starts on a fresh line
          // instead of butting up against the last line of this one.
          lineContentsRef.current = [...lineContentsRef.current, '']
          setLineContents(lineContentsRef.current)
          const spacerIdx = lineContentsRef.current.length - 1
          setLines(prev => [...prev, { kind: 'spacer' }])
          setClipPcts(prev => [...prev, 100])
          setVisibleCount(spacerIdx + 1)
          await new Promise(r => setTimeout(r, 600))
        }
        else if (data.event === 'BOARD_WRITE') {
          const content = data.payload?.content || ''
          const isLatex = data.payload?.render === 'latex'
          const line = (isLatex ? renderLine(content) : renderTextLine(content))
            || renderTextLine(content)
            || (content ? { isText: true, isHeading: false, html: escapeHtml(content) } : null)
          if (line) await pushAndReveal(line, null, content)
        }
        else if (data.event === 'BOARD_WRITE_START') {
          writeBufferRef.current = ''
          lineContentsRef.current = [...lineContentsRef.current, '']
          setLineContents(lineContentsRef.current)
          writeIndexRef.current = lineContentsRef.current.length - 1
          setLines(prev => [...prev, { isText: true, isHeading: false, kind: 'writing', html: '' }])
          setClipPcts(prev => [...prev, 100])
          setVisibleCount(prev => Math.max(prev, writeIndexRef.current + 1))
        }
        else if (data.event === 'BOARD_WRITE_APPEND') {
          const idx = writeIndexRef.current
          if (idx < 0) return
          writeBufferRef.current += data.payload?.content || ''
          const buf = writeBufferRef.current
          lineContentsRef.current[idx] = buf
          setLineContents([...lineContentsRef.current])
          setLines(prev => {
            const next = [...prev]
            if (next[idx]) next[idx] = { ...next[idx], html: escapeHtml(buf) }
            return next
          })
        }
        else if (data.event === 'BOARD_WRITE_COMPLETE') {
          const idx     = writeIndexRef.current
          const content = data.payload?.content ?? writeBufferRef.current
          const isLatex = data.payload?.render === 'latex'
          const finalLine = (isLatex ? renderLine(content) : renderTextLine(content))
            || renderTextLine(content)
            || { isText: true, isHeading: false, html: escapeHtml(content) }
          if (idx >= 0) {
            lineContentsRef.current[idx] = content
            setLineContents([...lineContentsRef.current])
            setLines(prev => {
              const next = [...prev]
              if (next[idx]) next[idx] = { ...finalLine, kind: 'math' }
              return next
            })
          }
          writeIndexRef.current  = -1
          writeBufferRef.current = ''
        }
        else if (data.event === 'BOARD_HIGHLIGHT' || data.event === 'BOARD_UNDERLINE' || data.event === 'BOARD_CIRCLE') {
          const target = data.payload?.content || ''
          const idx = findLineIndexForTarget(target)
          if (idx >= 0) {
            const key  = lineContentsRef.current[idx]
            const kind = data.event === 'BOARD_HIGHLIGHT' ? 'highlight'
                       : data.event === 'BOARD_UNDERLINE'  ? 'underline' : 'circle'
            boardAnnotationsRef.current = { ...boardAnnotationsRef.current, [key]: kind }
            setBoardAnnotations(boardAnnotationsRef.current)
          } else {
            console.warn(`${data.event}: no board line matched target "${target}"`, lineContentsRef.current)
          }
        }
        else if (data.event === 'BOARD_ANNOTATE') {
          const content = data.payload?.content || ''
          const line = renderTextLine(content, { isHeading: false })
            || { isText: true, isHeading: false, html: escapeHtml(content) }
          await pushAndReveal({ ...line, kind: 'annotation' }, null, content)
        }
        else if (data.event === 'BOARD_ERASE') {
          const target = data.payload?.content || 'all'
          if (target === 'all') {
            lineContentsRef.current = []; boardAnnotationsRef.current = {}
            setLines([]); setLineContents([]); setClipPcts([]); setVisibleCount(0)
            setBoardAnnotations({})
          } else {
            const idx = findLineIndexForTarget(target)
            if (idx >= 0) {
              const key = lineContentsRef.current[idx]
              lineContentsRef.current = lineContentsRef.current.filter((_, i) => i !== idx)
              setLineContents(lineContentsRef.current)
              setLines(prev => prev.filter((_, i) => i !== idx))
              setClipPcts(prev => prev.filter((_, i) => i !== idx))
              setVisibleCount(prev => Math.max(0, prev - 1))
              if (key !== undefined && key in boardAnnotationsRef.current) {
                const rest = { ...boardAnnotationsRef.current }
                delete rest[key]
                boardAnnotationsRef.current = rest
                setBoardAnnotations(rest)
              }
            }
          }
        }
        else if (data.event === 'BOARD_REVEAL') {
          const content = data.payload?.content || ''
          const line = renderLine(content) || renderTextLine(content)
          if (line) await pushAndReveal(line, null, content)
          // else: content wasn't renderable as a board line — previously
          // fell back to the narration panel, which no longer exists.
        }
        else if (data.event === 'TEACHER_SAYS') {
          // Narration panel removed — TEACHER_SAYS no longer renders
          // anywhere. Audio still plays via TEACHER_AUDIO_CHUNK below;
          // this event is otherwise a no-op now.
        }
        else if (data.event === 'TEACHER_AUDIO_CHUNK') {
          getAudioPlayer().enqueueChunk(data.payload?.data, data.payload?.sample_rate)
        }
        else if (data.event === 'TEACHER_AUDIO_ERROR') {
          // Non-fatal — voice_engine already fell back to silent, paced
          // words for this clause. Just log it; the lesson keeps moving.
          console.warn('Teacher audio error:', data.payload?.message)
        }
        else if (data.event === 'RESUME_BRIDGE') {
          // No-op now — was only used to reset the narration panel.
        }
        else if (data.event === 'STEP_PAUSE') {
          await new Promise(r => setTimeout(r, data.payload?.delay_ms || 500))
        }
        else if (data.event === 'HAND_RAISE_ACK') {
          // Backend noticed the raised hand at a group boundary but is still
          // finishing the current step — soft "noted" state, lesson keeps
          // playing. Only advance from 'raised'; ignore if the learner
          // already lowered it or it was already promoted to 'active'.
          setHandState(prev => (prev === 'raised' ? 'acknowledged' : prev))
        }
        else if (data.event === 'LEARNER_CHECKPOINT') {
          // drain(), not stop(): the backend has already fully sent this
          // narration's audio (it drains a full clause before emitting
          // this event) but the player schedules audio ahead of
          // currentTime for gapless playback, so some of it likely
          // hasn't been HEARD yet. stop() would hard-close the
          // AudioContext and cut that tail off mid-word.
          await getAudioPlayer().drain()
          setIsAwaitingPractice(true)
          setPlaying(false)
          setLuminaLabel('PRACTICE')
          setPracticePrompt(data.payload?.content || 'Your turn. Try to solve this.')
          await new Promise(r => setTimeout(r, 1500))
        }
        else if (data.event === 'LESSON_PAUSE') {
          es.close(); esRef.current = null
          await getAudioPlayer().drain()
          setPlaying(false)
          // Whatever resume call got us here has fully landed — release the
          // guard so the next checkpoint's submit/dismiss isn't blocked by
          // the previous one's in-flight flag.
          resumeInFlightRef.current = false

          const isHandTurn      = !!data.payload?.raised_as_hand
          const isAwaitResponse = data.payload?.pause_reason === 'AWAIT_RESPONSE'

          if (isHandTurn) {
            // A raised hand reflects explicit learner intent, so it takes
            // priority even if this pause also happens to land on an
            // automated practice checkpoint boundary (isAwaitResponse).
            // The scripted checkpoint can re-fire after the hand-turn
            // resolves; a human waiting to ask something shouldn't be
            // silently skipped in favor of an automated prompt.
            if (isAwaitResponse) {
              console.warn('LESSON_PAUSE carried both AWAIT_RESPONSE and raised_as_hand — resolving in favor of the hand-raise turn.')
            }
            setIsAwaitingPractice(false)

            if (handLowerRequestedRef.current) {
              // Learner cancelled their hand after the backend had already
              // committed to this pause (it was mid-sentence and could only
              // check at the boundary). There's no question to collect, so
              // resolve it by resuming automatically instead of forcing the
              // hand-turn box open or leaving the lesson stuck paused with
              // no visible control.
              handLowerRequestedRef.current = false
              setHandState('idle')
              triggerResume()
              setPlaying(true)
              openLessonSSE(sessionIdRef.current, true, {
                question:         null,
                question_type:    'GENERAL',
                approach_used:    'hand_lowered',
                core_explanation: 'Learner lowered their hand before the teacher could address it.',
              })
            } else {
              // Teacher just spoke the "I see your hand, what's your
              // question?" line and is now genuinely waiting. There's no
              // question text server-side yet (raise_hand() was called
              // without one) — so don't open the Explain board yet, just
              // reveal the hand-turn input and let the learner type.
              setHandState('active')
            }
          } else if (isAwaitResponse) {
            setIsAwaitingPractice(true)
          } else {
            setIsAwaitingPractice(false)
            setExplainVisible(true)
          }
        }
        else if (data.event === 'LESSON_COMPLETE') {
          es.close(); esRef.current = null
          resumeInFlightRef.current = false
          setProgress(100); setPlaying(false); setDone(true)
          setCompletedLessons(prev => new Set([...prev, currentLessonRef.current?.globalIndex]))
        }
        else if (data.event === 'ERROR') {
          es.close(); esRef.current = null
          resumeInFlightRef.current = false
          setPlaying(false)

          // Some backend signals arrive on the ERROR event but are not real
          // failures — they're pause/hand-raise/answer-turn bookkeeping
          // (stale duplicate connections, an in-flight AWAIT_RESPONSE pause,
          // a hand-raise turn already being handled elsewhere, etc). None of
          // these should ever surface as an error to the learner or offer a
          // "retry" — there's nothing broken and nothing to redo.
          const NON_FATAL_SIGNAL_CODES = [
            'ALREADY_RESUMED', 'AWAIT_RESPONSE', 'HAND_RAISE_ACTIVE', 'PAUSE_ACTIVE',
          ]
          if (NON_FATAL_SIGNAL_CODES.includes(data.payload?.code)) {
            console.warn(`Ignoring non-fatal signal (${data.payload?.code}) for ${sid}: ${data.payload?.message}`)
            return
          }

          showError(data.payload?.message || 'Stream error occurred.', () => {
            setPlaying(true)
            openLessonSSE(sid, isResume, resumeSummary)
          })
        }
      }).catch(err => console.error('Queue error:', err))
    }

    // Native connection-level failures (dropped connection, slow-start
    // timeout, server restart) — NOT the same as an in-band ERROR event
    // above. Without this handler, EventSource's default behavior is to
    // silently reconnect using the exact same URL, which for a resume
    // stream can re-invoke /stream/resume after the session has already
    // moved past PAUSED (see ALREADY_RESUMED handling above). Closing here
    // takes control away from that silent retry and surfaces one clear,
    // user-actionable error instead of a stale duplicate request.
    es.onerror = () => {
      if (esRef.current !== es) return // already closed/replaced; ignore
      es.close(); esRef.current = null
      resumeInFlightRef.current = false
      setPlaying(false)
    }
  }

  // ── openAnswerSSE ─────────────────────────────────────────────────────────
  // Connects to GET /stream/answer and plays the stored answer_engine envelope
  // through the RIGHT board using the identical event vocabulary and rendering
  // logic as openLessonSSE — BOARD_WRITE_START/APPEND/COMPLETE for char-by-char
  // writing, TEACHER_SAYS for the shared Lumina narration panel, LEARNER_CHECKPOINT
  // for the understanding probe, ANSWER_COMPLETE to close and re-enable input.
  //
  // Deliberately uses its own ref (answerEsRef) so it never clobbers esRef,
  // which tracks the lesson SSE (already closed at this point but will reopen
  // on resume).
  const openAnswerSSE = (sid) => {
    const es = new EventSource(`${API_BASE}/stream/answer?session_id=${sid}`)
    answerEsRef.current = es
    let queue = Promise.resolve()

    es.onmessage = (evt) => {
      let data
      try { data = JSON.parse(evt.data) } catch (e) { return }

      queue = queue.then(async () => {
        await waitIfPaused()

        // ── Section / step lifecycle ────────────────────────────────────────
        if (data.event === 'SECTION_START') {
          // Answer sections are always explanation-type — keep label neutral.
          setLuminaLabel('LUMINA')
        }
        else if (data.event === 'SECTION_END') {
          // Insert a blank row so the next section starts on a fresh line
          // instead of butting up against the last line of this one.
          const spacerId = explainLineIdCounterRef.current++
          explainLineContentsRef.current = [...explainLineContentsRef.current, '']
          explainLineIdsRef.current      = [...explainLineIdsRef.current, spacerId]
          setExplainLineContents([...explainLineContentsRef.current])
          setExplainLineIds([...explainLineIdsRef.current])
          const spacerIdx = explainLineContentsRef.current.length - 1
          setExplainLines(prev => [...prev, { kind: 'spacer' }])
          setExplainClipPcts(prev => [...prev, 100])
          setExplainVisibleCount(spacerIdx + 1)
          // Small inter-section breath (answers usually have one section).
          await new Promise(r => setTimeout(r, 300))
        }
        // STEP_START / STEP_END carry no board content — ignore silently.

        // ── Board writing (char-by-char, identical to left board) ───────────
        else if (data.event === 'BOARD_WRITE') {
          // Legacy / low-latency: full line in one shot.
          const content = data.payload?.content || ''
          const isLatex = data.payload?.render === 'latex'
          const line = (isLatex ? renderLine(content) : renderTextLine(content))
            || renderTextLine(content)
            || (content ? { isText: true, isHeading: false, html: escapeHtml(content) } : null)
          if (line) await pushAndRevealRight(line, content)
        }
        else if (data.event === 'BOARD_WRITE_START') {
          // Open an empty in-progress line; chars stream in via APPEND.
          explainWriteBufferRef.current = ''
          const newId = explainLineIdCounterRef.current++
          explainLineContentsRef.current = [...explainLineContentsRef.current, '']
          explainLineIdsRef.current      = [...explainLineIdsRef.current, newId]
          setExplainLineContents([...explainLineContentsRef.current])
          setExplainLineIds([...explainLineIdsRef.current])
          explainWriteIndexRef.current = explainLineContentsRef.current.length - 1
          setExplainLines(prev => [...prev, { isText: true, isHeading: false, kind: 'writing', html: '' }])
          setExplainClipPcts(prev => [...prev, 100])
          setExplainVisibleCount(prev => Math.max(prev, explainWriteIndexRef.current + 1))
        }
        else if (data.event === 'BOARD_WRITE_APPEND') {
          // KaTeX can't render partial LaTeX — show growing plain text and
          // snap to rendered form on COMPLETE, same as the left board.
          const idx = explainWriteIndexRef.current
          if (idx < 0) return
          explainWriteBufferRef.current += data.payload?.content || ''
          const buf = explainWriteBufferRef.current
          explainLineContentsRef.current[idx] = buf
          setExplainLineContents([...explainLineContentsRef.current])
          setExplainLines(prev => {
            const next = [...prev]
            if (next[idx]) next[idx] = { ...next[idx], html: escapeHtml(buf) }
            return next
          })
        }
        else if (data.event === 'BOARD_WRITE_COMPLETE') {
          const idx     = explainWriteIndexRef.current
          const content = data.payload?.content ?? explainWriteBufferRef.current
          const isLatex = data.payload?.render === 'latex'
          const finalLine = (isLatex ? renderLine(content) : renderTextLine(content))
            || renderTextLine(content)
            || { isText: true, isHeading: false, html: escapeHtml(content) }
          if (idx >= 0) {
            explainLineContentsRef.current[idx] = content
            setExplainLineContents([...explainLineContentsRef.current])
            setExplainLines(prev => {
              const next = [...prev]
              if (next[idx]) next[idx] = { ...finalLine, kind: 'math' }
              return next
            })
          }
          explainWriteIndexRef.current  = -1
          explainWriteBufferRef.current = ''
        }

        // ── Board annotations ───────────────────────────────────────────────
        else if (data.event === 'BOARD_HIGHLIGHT' || data.event === 'BOARD_UNDERLINE' || data.event === 'BOARD_CIRCLE') {
          const target = data.payload?.content || ''
          const idx = findExplainLineIndexForTarget(target)
          if (idx >= 0) {
            const key  = explainLineIdsRef.current[idx]
            const kind = data.event === 'BOARD_HIGHLIGHT' ? 'highlight'
                       : data.event === 'BOARD_UNDERLINE'  ? 'underline' : 'circle'
            setExplainAnnotations(prev => ({ ...prev, [key]: kind }))
          } else {
            console.warn(`${data.event}: no explain-board line matched target "${target}"`, explainLineContentsRef.current)
          }
        }
        else if (data.event === 'BOARD_ANNOTATE') {
          const content = data.payload?.content || ''
          const line = renderTextLine(content, { isHeading: false })
            || { isText: true, isHeading: false, html: escapeHtml(content) }
          await pushAndRevealRight({ ...line, kind: 'annotation' }, content)
        }
        else if (data.event === 'BOARD_ERASE') {
          const target = data.payload?.content || 'all'
          if (target === 'all') {
            explainLineContentsRef.current = []
            explainLineIdsRef.current      = []
            setExplainLines([]); setExplainLineContents([]); setExplainLineIds([])
            setExplainClipPcts([]); setExplainVisibleCount(0)
            setExplainAnnotations({})
          } else {
            const idx = findExplainLineIndexForTarget(target)
            if (idx >= 0) {
              const key = explainLineIdsRef.current[idx]
              explainLineContentsRef.current = explainLineContentsRef.current.filter((_, i) => i !== idx)
              explainLineIdsRef.current      = explainLineIdsRef.current.filter((_, i) => i !== idx)
              setExplainLineContents([...explainLineContentsRef.current])
              setExplainLineIds([...explainLineIdsRef.current])
              setExplainLines(prev => prev.filter((_, i) => i !== idx))
              setExplainClipPcts(prev => prev.filter((_, i) => i !== idx))
              setExplainVisibleCount(prev => Math.max(0, prev - 1))
              setExplainAnnotations(prev => {
                if (key !== undefined && key in prev) {
                  const rest = { ...prev }; delete rest[key]; return rest
                }
                return prev
              })
            }
          }
        }
        else if (data.event === 'BOARD_REVEAL') {
          const content = data.payload?.content || ''
          const line = renderLine(content) || renderTextLine(content)
          if (line) await pushAndRevealRight(line, content)
          // else: content wasn't renderable as a board line — previously
          // fell back to the narration panel, which no longer exists.
        }

        // ── Narration ───────────────────────────────────────────────────────
        else if (data.event === 'TEACHER_SAYS') {
          // Narration panel removed — no longer rendered anywhere.
        }
        else if (data.event === 'TEACHER_AUDIO_CHUNK') {
          getAudioPlayer().enqueueChunk(data.payload?.data, data.payload?.sample_rate)
        }
        else if (data.event === 'TEACHER_AUDIO_ERROR') {
          console.warn('Answer audio error:', data.payload?.message)
        }
        else if (data.event === 'STEP_PAUSE') {
          await new Promise(r => setTimeout(r, data.payload?.delay_ms || 500))
        }

        // ── Understanding probe ─────────────────────────────────────────────
        else if (data.event === 'LEARNER_CHECKPOINT') {
          // The answer envelope's AWAIT_RESPONSE event IS the probe question —
          // this is the answer stream's equivalent of the lesson stream's
          // LESSON_PAUSE: the backend hands control back to the learner right
          // here and ends its side of the connection without a following
          // ANSWER_COMPLETE (there's nothing left to stream once the probe
          // question has been asked). Close proactively, the same way
          // openLessonSSE's LESSON_PAUSE handler does, so this expected,
          // by-design closure isn't picked up by the browser's EventSource
          // as a dropped connection and reported as an error.
          setLuminaLabel('PRACTICE')
          setExplainPrompt(data.payload?.content || 'Does that make sense? Try it yourself.')
          await new Promise(r => setTimeout(r, 800))
          es.close(); answerEsRef.current = null
          setExplainLoading(false)
        }

        // ── Terminal events ─────────────────────────────────────────────────
        else if (data.event === 'ANSWER_COMPLETE') {
          // Stream finished cleanly — disable loading state so the follow-up
          // input becomes active and the learner can type their response.
          es.close(); answerEsRef.current = null
          setExplainLoading(false)
        }
        else if (data.event === 'ERROR') {
          es.close(); answerEsRef.current = null
          setExplainLoading(false)

          // Mirror openLessonSSE's guard: an answer/ask turn transitioning
          // (e.g. CONFIRMED handing back to the lesson stream, or a probe/
          // hand-raise state settling) is not a failure and must never
          // surface as one.
          const NON_FATAL_SIGNAL_CODES = [
            'ALREADY_RESUMED', 'AWAIT_RESPONSE', 'HAND_RAISE_ACTIVE', 'PAUSE_ACTIVE',
          ]
          if (NON_FATAL_SIGNAL_CODES.includes(data.payload?.code)) {
            console.warn(`Ignoring non-fatal signal (${data.payload?.code}) for ${sid}: ${data.payload?.message}`)
            return
          }

          showError(data.payload?.message || 'Something went wrong getting that answer.', () => {
            setExplainLoading(true)
            openAnswerSSE(sid)
          })
        }
        // HEARTBEAT and unknown events ignored.

      }).catch(err => console.error('Answer queue error:', err))
    }

    // See the matching comment in openLessonSSE — without this, a dropped
    // connection is silently retried by the browser instead of surfaced.
    es.onerror = () => {
      if (answerEsRef.current !== es) return
      es.close(); answerEsRef.current = null
      setExplainLoading(false)
    }
  }

  // ── handleLearnerQuestion ─────────────────────────────────────────────────
  const handleLearnerQuestion = async (question) => {
    if (!sessionIdRef.current) return
    setCurrentQuestion(question)
    try {
      await fetch(`${API_BASE}/stream/pause`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionIdRef.current, question }),
      })
    } catch (e) {
      console.error('Failed to pause lesson stream', e)
      showError('Could not send your question to the teacher. Please try again.', () => handleLearnerQuestion(question))
    }
  }

  // ── handleRaiseHand ───────────────────────────────────────────────────────
  // Toggle: idle → raised (POST /stream/hand-raise). Tapping again while
  // 'raised' or 'acknowledged' cancels it (POST /stream/hand-lower) before
  // the teacher gets to it. No-op once 'active' — at that point the hand
  // is already down server-side; use the hand-turn input instead.
  const handleRaiseHand = async () => {
    if (!sessionIdRef.current) return

    if (handState === 'raised' || handState === 'acknowledged') {
      setHandState('idle')
      // Mark that a lower was requested. If the backend already committed
      // to a raised_as_hand pause before this reaches it (it was mid-
      // sentence and only checks at the next boundary), the LESSON_PAUSE
      // handler below will see this flag and resolve the stale pause
      // instead of forcing the hand-turn box back open.
      handLowerRequestedRef.current = true
      try {
        const res = await fetch(`${API_BASE}/stream/hand-lower`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionIdRef.current }),
        })
        if (!res.ok) {
          // Unlike the raise path, we don't revert to 'raised' here — the
          // learner already asked to cancel and the UI already reflects
          // that. If the backend never got the message in time, the
          // handLowerRequestedRef fallback in the LESSON_PAUSE handler
          // resolves the stale pause automatically instead.
          console.warn(`Hand-lower request failed: ${res.status}`)
        }
      } catch (e) {
        console.error('Failed to lower hand', e)
      }
      return
    }

    if (handState !== 'idle') return

    handLowerRequestedRef.current = false
    setHandState('raised')
    try {
      const res  = await fetch(`${API_BASE}/stream/hand-raise`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionIdRef.current }),
      })
      if (!res.ok) throw new Error(`Hand-raise request failed: ${res.status}`)
      const data = await res.json()
      if (!data.acknowledged) {
        // Backend didn't actually set the flag — e.g. the session wasn't
        // STREAMING/RESUMING at that moment (mid-pause, mid-resume-bridge,
        // etc; see data.reason). Nothing was raised server-side, so the
        // optimistic 'raised' state would otherwise sit forever waiting
        // for a HAND_RAISE_ACK / LESSON_PAUSE that's never coming.
        console.warn('Hand-raise not acknowledged by backend:', data.reason)
        setHandState('idle')
      }
    } catch (e) {
      console.error('Failed to raise hand', e)
      setHandState('idle')
      showError('Could not raise your hand. Please try again.', () => handleRaiseHand())
    }
  }

  // ── handleHandTurnSubmit ──────────────────────────────────────────────────
  // The lesson is already paused server-side (LESSON_PAUSE already fired)
  // — no /stream/pause call needed here. Just set the question the same
  // way the normal ask-a-question path does, so the existing
  // explainVisible effect (line ~203) picks it up and drives the same
  // answer_engine flow as any other question.
  const handleHandTurnSubmit = () => {
    const q = handQuestionInput.trim()
    if (!q) return
    setHandQuestionInput('')
    setHandState('idle')
    setCurrentQuestion(q)
    setExplainVisible(true)
  }

  // ── handlePracticeSubmit ──────────────────────────────────────────────────
  const handlePracticeSubmit = () => {
    const attempt = practiceInput.trim()
    setPracticeInput('')
    setIsAwaitingPractice(false)
    setPracticePrompt('')
    triggerResume()
    setPlaying(true)
    openLessonSSE(sessionIdRef.current, true, {
      question:         currentQuestion || 'Practice attempt',
      question_type:    'PRACTICE_ATTEMPT',
      approach_used:    'attempt',
      core_explanation: attempt || 'Student submitted practice attempt.',
    })
  }

  // ── handleDismissQA ───────────────────────────────────────────────────────
  const handleDismissQA = () => {
    setExplainVisible(false)
    finishExplainTurn()
    triggerResume()
    if (sessionIdRef.current) {
      setPlaying(true)
      openLessonSSE(sessionIdRef.current, true, {
        question:         currentQuestion,
        question_type:    'GENERAL',
        approach_used:    'dismissed',
        core_explanation: 'Student resumed the lesson without confirming understanding.',
      })
    }
    setQaState({
      examplesGiven: 0, previousApproach: null, approachesUsed: [],
      conversationHistory: [], probeQuestion: null, awaitingProbeResponse: false,
      awaitingFinalConfirmation: false, boardState: [], coreExplanation: null,
    })
  }

  // ── handleExplainQuestion ─────────────────────────────────────────────────
  // Drives the right-board Q&A conversation.
  // Turn 1 (auto-triggered by the explainVisible effect): calls handleAskBackend
  //   → gets { readyToStream: true } → opens answer SSE on the right board.
  // Turn 2+ (learner types in explainInput): same path until CONFIRMED, which
  //   returns { resumed: true } and resumes the lesson SSE.
  const handleExplainQuestion = async (learnerInput) => {
    if (explainLoading) return
    if (qaState.conversationHistory.length === 0) pushExplainDivider(learnerInput)
    setExplainLoading(true)
    setExplainPrompt('')
    try {
      const result = await handleAskBackend(learnerInput)
      if (!result || result.resumed) {
        // Understanding confirmed — handleAskBackend already reopened the lesson
        // SSE. Keep everything written so far as notes; just close out this
        // turn's SSE/loading state so the board is ready for the next question.
        finishExplainTurn()
        return
      }
      if (result.readyToStream) {
        // Answer envelope is stored in the session; open the SSE stream.
        // explainLoading stays true — openAnswerSSE sets it to false on ANSWER_COMPLETE.
        openAnswerSSE(sessionIdRef.current)
        return
      }
    } catch (err) {
      console.error('Explain error:', err)
      setExplainLoading(false)
      showError(err.message || 'Something went wrong. Please try again.', () => handleExplainQuestion(learnerInput))
    }
  }

  // ── handleAskBackend (Q&A loop) ───────────────────────────────────────────
  // Posts to /answer/ask with session_id so the backend can store the answer
  // envelope and return a lightweight { status: "ready_to_stream" } instead of
  // the full JSON blob. The content arrives via GET /stream/answer SSE.
  // RESUME actions (understanding confirmed) still return synchronously so the
  // lesson stream can reopen immediately.
  const handleAskBackend = async (learnerInput) => {
    const isFollowUp      = qaState.conversationHistory.length > 0
    const isProbeResponse = qaState.awaitingProbeResponse

    const payload = {
      session_id:           sessionIdRef.current,
      question:             currentQuestion,
      active_segment:       activeSegment,
      teaching_script:      teachingScript,
      learner_response:     isProbeResponse ? null : (isFollowUp ? learnerInput : null),
      conversation_history: qaState.conversationHistory,
      examples_given:       qaState.examplesGiven,
      previous_approach:    qaState.previousApproach,
      approaches_used:      qaState.approachesUsed,
      question_bank:        questionBank,
      confusion_location:   isProbeResponse ? learnerInput : null,
      probe_question:       qaState.probeQuestion,
      model:                null,
      board_state:           qaState.boardState,
      awaiting_final_confirmation: qaState.awaitingFinalConfirmation,
      core_explanation:      qaState.coreExplanation,
    }

    const res = await fetch(`${API_BASE}/answer/ask`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || `Explain error ${res.status}`)
    }

    const data = await res.json()

    // Update Q&A bookkeeping from the lightweight response fields.
    // probe_question is stored so it can be echoed back to the backend on the
    // next turn for understanding classification context. core_explanation is
    // stored the same way — it's the one-line summary of what was actually
    // explained, needed so the resume bridge isn't contextless (see
    // handle_answer_session / _build_resume_bridge_prompt).
    setQaState(prev => ({
      ...prev,
      examplesGiven:        data.examples_given          ?? prev.examplesGiven,
      previousApproach:     data.approaches_used?.slice(-1)[0] ?? prev.previousApproach,
      approachesUsed:       data.approaches_used          ?? prev.approachesUsed,
      probeQuestion:        data.probe_question           ?? null,
      awaitingProbeResponse: data.action === 'PROBE',
      awaitingFinalConfirmation: data.awaiting_final_confirmation ?? false,
      boardState:            data.board_state ?? prev.boardState,
      coreExplanation:       data.core_explanation ?? prev.coreExplanation,
      conversationHistory: [
        ...prev.conversationHistory,
        { role: 'user',      content: isFollowUp ? learnerInput : currentQuestion },
        // Store the actual substance of what was explained, not the probe
        // question — the probe is a check-for-understanding question, not
        // the teacher's turn in the conversation. Falls back to the probe
        // text only if no core_explanation came back this turn.
        { role: 'assistant', content: data.core_explanation || data.probe_question || '' },
      ],
    }))

    // CONFIRMED — understanding resolved; reopen lesson stream.
    if (data.understanding_status === 'CONFIRMED' || data.resume_lesson) {
      setExplainVisible(false)
      triggerResume()
      setPlaying(true)
      openLessonSSE(sessionIdRef.current, true, {
        question:         currentQuestion,
        question_type:    'GENERAL',
        approach_used:    data.approaches_used?.slice(-1)[0] || 'initial',
        core_explanation: data.core_explanation || 'Student confirmed understanding.',
      })
      setQaState({
        examplesGiven: 0, previousApproach: null, approachesUsed: [],
        conversationHistory: [], probeQuestion: null, awaitingProbeResponse: false,
        awaitingFinalConfirmation: false, boardState: [], coreExplanation: null,
      })
      return { resumed: true }
    }

    // Any other action (ANSWER / ESCALATE / PROBE / MICRO) — envelope is
    // stored in the session; caller opens GET /stream/answer to receive it.
    return { readyToStream: true }
  }

  // ── handleLessonClick — 3-stage pipeline (plan → anticipate → session) ────
  const handleLessonClick = async (item) => {
    if (!isLessonUnlocked(item.globalIndex)) return

    const lesson = item.lessonObj
    resetBoard()
    setCurrentLesson(item)
    setLoadingStage('plan')
    setAiExplanation([])
    setVisibleExplanations(0)
    clearError()

    const weakPrereqs = courseData?.prerequisites
      ? Object.entries(courseData.prerequisites)
          .filter(([, rating]) => Number(rating) <= 2)
          .map(([label]) => label)
      : []

    const sharedPayload = {
      lesson_id:             lesson.id     || `lesson_${item.globalIndex}`,
      lesson_title:          lesson.title  || item.label,
      key_concepts:          Array.isArray(lesson.key_concepts) ? lesson.key_concepts : [],
      prerequisite_revision: lesson.prerequisite_revision || '',
      description:           lesson.description || '',
      subject:               courseData?.courseDetails?.subject    || 'General',
      grade_level:           courseData?.courseDetails?.grade_level || 'Not specified',
      goal:                  courseData?.courseDetails?.goal        || 'Deep Mastery',
      weak_prerequisites:    weakPrereqs.length > 0 ? weakPrereqs : null,
      source_context:        courseData?.source_summary ?? null,
      model:                 null,
    }

    try {
      setLoadingStage('plan')
      const planRes = await fetch(`${API_BASE}/lesson/generate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(sharedPayload),
      })
      if (!planRes.ok) throw new Error('Lesson plan error')
      const lessonPlan = await planRes.json()
      setTeachingScript(lessonPlan)


      setLoadingStage('session')
      const sessionRes = await fetch(`${API_BASE}/stream/session/create`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ teaching_script: lessonPlan}),
      })
      if (!sessionRes.ok) throw new Error('Failed to create session')

      const sessionData = await sessionRes.json()
      setSessionId(sessionData.session_id)
      totalSegmentsRef.current = lessonPlan?.sections?.length || 0

      setLoadingStage(null)
      setPlaying(true)
      setSourceMode('lesson')
      openLessonSSE(sessionData.session_id)

    } catch (e) {
      setLoadingStage(null)
      setPlaying(false)
      showError(e.message || 'Failed to initialize lesson. Please retry.', () => handleLessonClick(item))
    }
  }

  // ── runPreset ─────────────────────────────────────────────────────────────
  const runPreset = async (parsed) => {
    resetBoard()
    setPlaying(true)
    setSourceMode('preset')
    for (let i = 0; i < parsed.length; i++) {
      await pushAndReveal(parsed[i], parsed.length)
    }
    setProgress(100)
    setPlaying(false)
    setDone(true)
  }

  const handlePreset = (latex) => {
    const parsed = parseLatexLines(latex)
    if (parsed.length === 0) return
    runPreset(parsed)
  }

  const handleCustomWrite = () => {
    if (!customLatex.trim()) return
    const parsed = parseLatexLines(customLatex)
    if (parsed.length === 0) { showError('No valid LaTeX lines found.'); return }
    runPreset(parsed)
  }

  const handleReplay = () => {
    if (sourceMode === 'preset') return
    handleCustomWrite()
  }

  // ── courseSections ────────────────────────────────────────────────────────
  const courseSections = (() => {
    const chapters = courseData?.coursePlan?.chapters
    if (!chapters?.length) return null
    let globalIdx = -1
    return chapters.map((ch, chIdx) => {
      const chapterId = ch.id || String(chIdx)
      const items = (ch.lessons || []).map((lesson, lIdx) => {
        globalIdx++
        const lessonTitle = typeof lesson === 'string' ? lesson : (lesson.title || `Lesson ${lIdx + 1}`)
        return { label: lessonTitle, globalIndex: globalIdx, lessonObj: lesson, chapterId, lessonIndex: lIdx }
      })
      return { category: ch.title, chapterId, chapterType: ch.type || '', estimatedDuration: ch.estimated_duration || '', items }
    })
  })()

  const hasCourse = !!courseSections

  const isLessonUnlocked = (globalIndex) =>
    globalIndex === 0 || completedLessons.has(globalIndex - 1) || completedLessons.has(globalIndex)

  const activeStageIdx = loadingStage
    ? LOADING_STAGES.findIndex(s => s.key === loadingStage)
    : -1

  const {
    labelColor: luminaLabelColor,
    borderColor: luminaBorderColor,
    bgColor: luminaBgColor,
  } = getLuminaTheme(luminaLabel)

  // ════════════════════════════════════════════════════════════════════════════
  // RENDER
  // ════════════════════════════════════════════════════════════════════════════
  return (
    <div style={S.root}>
      <div style={S.mesh} aria-hidden />
      <div style={S.grid} aria-hidden />

      <div style={S.particleLayer} aria-hidden>
        {PARTICLES.map((p, i) => (
          <span key={i} style={{
            position: 'absolute', left: p.x, top: p.y,
            fontSize: p.size, color: '#63c8ff',
            fontFamily: '"Crimson Pro", Georgia, serif',
            opacity: 0.04, userSelect: 'none', pointerEvents: 'none',
            animation: `floatUp ${p.dur} ease-in-out ${p.delay} infinite`,
          }}>{p.char}</span>
        ))}
      </div>

      {/* ── Header ── */}
      <header style={S.header}>
        <div style={S.headerLeft}>
          <button className="si-back" style={S.backBtn} onClick={onBack}>
            <span style={{ display: 'inline-flex', alignItems: 'center', marginRight: '6px' }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
            </span>
            Back
          </button>
          <div style={S.headerDivider} />
          <span style={S.headerTitle}>
            {courseData?.courseDetails?.topic || 'Interactive Lesson Board'}
          </span>
        </div>
      </header>

      <div style={S.layout}>

        {/* ── Main board area ── */}
        <main style={S.main}>

          {/* ─────────────────────────────────────────────────────────────────
               SPLIT CHALKBOARD
               Left : main lesson content  (independently scrollable)
               Right: Q&A / explanations   (independently scrollable)
          ─────────────────────────────────────────────────────────────────── */}
          <div
            className="lumina-board-shell"
            style={{
              ...S.boardShell,
              position: 'relative', display: 'flex', flexDirection: 'row',
              padding: 0, overflow: 'hidden', gap: 0,
            }}
          >
            <style>{`
              .lumina-pause-btn { opacity: 0; pointer-events: none; transition: opacity 0.2s ease; }
              .lumina-board-shell:hover .lumina-pause-btn { opacity: 1; pointer-events: auto; }
            `}</style>

            {/* ── Hover-to-reveal pause/resume — centered over the whole
                 board (both panels). Pauses/resumes the active board
                 stream(s) AND the teacher's voice together. Only shown
                 while something is actually playing/streaming. ─────────── */}
            {sourceMode === 'lesson' && loadingStage === null && !done && (playing || (explainVisible && explainLoading) || boardPaused) && (
              <div className="lumina-pause-btn" style={{
                position: 'absolute', top: '50%', left: '50%',
                transform: 'translate(-50%, -50%)', zIndex: 30,
              }}>
                <button
                  onClick={handleTogglePause}
                  title={boardPaused ? 'Resume' : 'Pause'}
                  style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    width: 56, height: 56, borderRadius: '50%',
                    background: 'rgba(10,14,20,0.72)',
                    border: '1px solid rgba(226,244,255,0.28)',
                    boxShadow: '0 4px 24px rgba(0,0,0,0.35)',
                    backdropFilter: 'blur(6px)',
                    cursor: 'pointer', color: 'rgba(226,244,255,0.92)',
                  }}
                >
                  {boardPaused ? (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><polygon points="6 4 20 12 6 20 6 4"></polygon></svg>
                  ) : (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg>
                  )}
                </button>
              </div>
            )}

            {/* ── Error overlay — chalked onto the center of the board itself
                 instead of a banner at the top of the screen. Covers both
                 panels so it reads as "the board" pausing to show the
                 problem, with Retry/Dismiss centered underneath the message.
                 NOTE: this only ever reflects genuine failures — normal
                 pause-driven transitions (AWAIT_RESPONSE, hand-raise state
                 changes, answer/ask turns) never call showError; see the
                 LESSON_PAUSE / HAND_RAISE_ACK / handleAskBackend branches. ── */}
            {error && (
              <div style={{
                position: 'absolute', inset: 0, zIndex: 40,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: 'rgba(10,14,20,0.55)', backdropFilter: 'blur(2px)',
              }}>
                <div style={{
                  display: 'flex', flexDirection: 'column', alignItems: 'center',
                  gap: 18, maxWidth: 460, padding: '32px 40px', textAlign: 'center',
                }}>
                  <span style={{ display: 'flex', color: '#f4b9b9' }}>
                    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                  </span>
                  <p style={{
                    margin: 0, fontFamily: "'Crimson Pro', Georgia, serif",
                    fontSize: 19, lineHeight: 1.6,
                    color: mode.text || '#e2f4ff',
                    textShadow: `0 0 12px ${(mode.text || '#e2f4ff')}44`,
                    letterSpacing: '0.01em',
                  }}>
                    {error}
                  </p>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 4 }}>
                    {retryAction && (
                      <button
                        onClick={() => { const retry = retryAction; clearError(); retry() }}
                        style={{
                          padding: '9px 24px', borderRadius: 8,
                          border: '1px solid rgba(99,200,255,0.4)',
                          background: 'rgba(99,200,255,0.12)', color: '#63c8ff',
                          fontSize: 12, letterSpacing: '0.08em', textTransform: 'uppercase',
                          cursor: 'pointer', fontFamily: 'inherit', fontWeight: 600,
                        }}
                      >
                        Retry
                      </button>
                    )}
                    <button
                      onClick={clearError}
                      style={{
                        padding: '9px 20px', borderRadius: 8,
                        border: '1px solid rgba(226,244,255,0.15)',
                        background: 'transparent', color: 'rgba(226,244,255,0.5)',
                        fontSize: 12, letterSpacing: '0.08em', textTransform: 'uppercase',
                        cursor: 'pointer', fontFamily: 'inherit',
                      }}
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* ── LEFT PANEL — Lesson content ──────────────────────────── */}
            <div style={{
              flex: '3 1 0', minWidth: 0,
              display: 'flex', flexDirection: 'column', overflow: 'hidden',
            }}>
              <div
                ref={boardRef}
                onScroll={() => {
                  const el = boardRef.current
                  if (!el) return
                  userScrolled.current = (el.scrollHeight - el.scrollTop - el.clientHeight) > 40
                }}
                style={{ ...S.boardInner, flex: 1, minHeight: 0, overflowY: 'auto', borderRadius: 0 }}
              >
                {loadingStage !== null ? (
                  <div style={{
                    position: 'absolute', inset: 0,
                    display: 'flex', flexDirection: 'column',
                    alignItems: 'center', justifyContent: 'center',
                    gap: 32, pointerEvents: 'none',
                  }}>
                    <div style={{ position: 'relative', width: 64, height: 64 }}>
                      <div style={{
                        width: 64, height: 64, borderRadius: '50%',
                        border: '1.5px solid rgba(99,200,255,0.10)',
                        borderTopColor: 'rgba(99,200,255,0.55)',
                        animation: 'spin 1.1s linear infinite',
                        boxShadow: '0 0 24px rgba(99,200,255,0.08)',
                      }} />
                      <span style={{
                        position: 'absolute', inset: 0,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: 22, animation: 'stagePulse 1.8s ease-in-out infinite',
                      }}>
                        {LOADING_STAGES[activeStageIdx]?.icon}
                      </span>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 }}>
                      {LOADING_STAGES.map((stage, idx) => {
                        const isPast    = idx < activeStageIdx
                        const isCurrent = idx === activeStageIdx
                        return (
                          <div key={stage.key} style={{
                            display: 'flex', alignItems: 'center', gap: 10,
                            opacity: isCurrent ? 1 : isPast ? 0.35 : 0.15,
                            animation: isCurrent ? 'stageFadeIn 0.4s ease-out forwards' : 'none',
                            transition: 'opacity 0.4s ease',
                          }}>
                            <div style={{
                              width: 6, height: 6, borderRadius: '50%',
                              background: isCurrent ? '#63c8ff' : isPast ? 'rgba(99,200,255,0.4)' : 'rgba(226,244,255,0.15)',
                              boxShadow: isCurrent ? '0 0 8px rgba(99,200,255,0.6)' : 'none',
                            }} />
                            <span style={{
                              fontSize: 13, letterSpacing: '0.07em',
                              color: isCurrent ? 'rgba(226,244,255,0.9)' : 'rgba(226,244,255,0.4)',
                              fontFamily: 'inherit',
                              display: 'flex', alignItems: 'center', gap: 6,
                            }}>
                              {isPast && <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>}
                              {stage.label}
                            </span>
                            {isCurrent && (
                              <span style={{ display: 'flex', gap: 3 }}>
                                {[0, 1, 2].map(d => (
                                  <span key={d} style={{
                                    width: 3, height: 3, borderRadius: '50%',
                                    background: 'rgba(99,200,255,0.7)', display: 'inline-block',
                                    animation: `dotBlink 1.2s ${d * 0.2}s ease-in-out infinite`,
                                  }} />
                                ))}
                              </span>
                            )}
                          </div>
                        )
                      })}
                    </div>

                    {currentLesson && (
                      <div style={{
                        fontSize: 11, letterSpacing: '0.1em',
                        color: 'rgba(226,244,255,0.22)', textTransform: 'uppercase',
                        maxWidth: 280, textAlign: 'center', lineHeight: 1.5,
                      }}>
                        {currentLesson.label}
                      </div>
                    )}
                  </div>

                ) : aiLoading ? (
                  <div style={S.emptyBoardState}>
                    <div style={{
                      width: 56, height: 56, borderRadius: '50%',
                      border: '2px solid rgba(99,200,255,0.18)',
                      borderTopColor: '#63c8ff',
                      animation: 'spin 1s linear infinite',
                      marginBottom: 14,
                      boxShadow: '0 0 20px rgba(99,200,255,0.12)',
                    }} />
                    <div style={{ fontSize: 15, letterSpacing: '0.08em', color: 'rgba(226,244,255,0.75)' }}>
                      Thinking…
                    </div>
                  </div>

                ) : lines.length > 0 ? (
                  <div style={S.boardContent}>
                    {lines.map((line, i) => {
                      const pct        = clipPcts[i] ?? 0
                      const isText     = !!line.isText
                      const isHeading  = !!line.isHeading
                      const isWriting  = line.kind === 'writing'
                      const isNote     = line.kind === 'annotation'
                      const annotation = boardAnnotations[lineContents[i]]

                      if (line.kind === 'spacer') {
                        return <div key={i} aria-hidden="true" style={{ width: '100%', height: 18 }} />
                      }

                      return (
                        <div key={i} style={{
                          opacity: i < visibleCount ? 1 : 0,
                          transition: 'opacity 0.25s ease',
                          width: '100%', display: 'flex', justifyContent: 'flex-start',
                        }}>
                          <div style={{
                            fontSize:      isNote ? 13 : 15,
                            color:         mode.text || '#e2f4ff',
                            textShadow:    `0 0 12px ${(mode.text || '#e2f4ff')}44`,
                            lineHeight:    isText ? 1.58 : 0.2,
                            margin:        0,
                            padding:       isText ? (isHeading ? '10px 0 2px' : '5px 0') : '5px 0px',
                            userSelect:    isText ? 'text' : 'none',
                            display:       annotation ? 'inline-block' : (isText ? 'block' : 'inline-block'),
                            maxWidth:      isText ? 'min(820px, 100%)' : 'none',
                            width:         annotation ? 'auto' : (isText ? '100%' : 'auto'),
                            textAlign:     'left',
                            letterSpacing: isHeading ? '0.12em' : '0.01em',
                            fontWeight:    isText && !isHeading ? 500 : undefined,
                            fontStyle:     isNote ? 'italic' : 'normal',
                            opacity:       isNote ? 0.75 : 1,
                            whiteSpace:    isText ? 'normal' : 'nowrap',
                            wordBreak:     'break-word',
                            clipPath:      `inset(0 ${100 - pct}% 0 0)`,
                            background:         annotation === 'highlight' ? 'rgba(255,210,80,0.16)' : 'transparent',
                            borderRadius:       annotation === 'highlight' ? 4 : (annotation === 'circle' ? 6 : 0),
                            textDecoration:     annotation === 'underline' ? 'underline' : 'none',
                            textDecorationColor: annotation === 'underline' ? 'rgba(99,200,255,0.7)' : 'transparent',
                            outline:            annotation === 'circle' ? '2px solid rgb(255, 255, 255)' : 'none',
                            outlineOffset:      annotation === 'circle' ? 4 : 0,
                            boxShadow:          annotation === 'circle' ? '0 0 10px rgb(240, 242, 243)' : 'none',
                          }}
                            dangerouslySetInnerHTML={{ __html: line.html + (isWriting ? '<span style="display:inline-block;width:1.5px;height:0.9em;background:currentColor;vertical-align:text-bottom;margin-left:2px;animation:blink 0.75s ease-in-out infinite alternate"></span>' : '') }}
                          />
                        </div>
                      )
                    })}
                  </div>

                ) : (
                  !playing && (
                    <div style={S.emptyBoardState}>
                      <div style={{ ...S.emptyIcon, display: 'flex', justifyContent: 'center', marginBottom: '16px' }}>
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2l3 7 7 3-7 3-3 7-3-7-7-3 7-3z"></path></svg>
                      </div>
                      Select lesson to start
                    </div>
                  )
                )}

                {playing && sourceMode === 'custom' && (
                  <div style={S.streamingIndicator}>STREAMING DATA</div>
                )}
              </div>
            </div>

            {/* ── CHALK DIVIDER ─────────────────────────────────────────── */}
            <div style={{
              width: 16, flexShrink: 0, position: 'relative',
              display: 'flex', alignItems: 'stretch',
            }}>
              <div style={{
                position: 'absolute', top: 28, bottom: 28, left: '50%',
                transform: 'translateX(-50%)', width: 2,
                background: 'linear-gradient(to bottom, transparent, rgba(226,244,255,0.13) 12%, rgba(226,244,255,0.10) 88%, transparent)',
                borderRadius: 2,
              }} />
              <div style={{
                position: 'absolute', top: 28, bottom: 28, left: '50%',
                transform: 'translateX(-50%)', width: 2,
                backgroundImage: 'repeating-linear-gradient(to bottom, rgba(226,244,255,0.12) 0px, rgba(226,244,255,0.12) 7px, transparent 7px, transparent 12px)',
                borderRadius: 2,
              }} />
            </div>

            {/* ── RIGHT PANEL — Q&A / Explanations ─────────────────────── */}
            <div style={ES.container}>

              {/* Header + dismiss */}
              <div style={ES.header}>
                <span style={{
                  ...ES.headerTitle,
                  color: explainVisible ? 'rgba(185,120,255,0.35)' : 'rgba(226,244,255,0.10)',
                }}>
                  Q&A · Explanations
                </span>
                {explainVisible && (
                  <button
                    onClick={handleDismissQA}
                    title="Resume lesson"
                    style={{ ...ES.resumeBtn, cursor: 'pointer' }}
                  >
                    Resume →
                  </button>
                )}
              </div>

              {/* Scrollable board — identical rendering logic to the left panel */}
              <div
                ref={explainBoardRef}
                onScroll={() => {
                  const el = explainBoardRef.current
                  if (!el) return
                  explainUserScrolled.current = (el.scrollHeight - el.scrollTop - el.clientHeight) > 40
                }}
                style={{ ...S.boardInner, ...ES.scrollArea }}
              >
                {explainLines.length === 0 ? (
                  !explainVisible ? (
                    <div style={ES.idleState}>
                    </div>
                  ) : (
                    <div style={ES.loadingState}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        {[0, 1, 2].map(d => (
                          <span key={d} style={{
                            width: 9, height: 9, borderRadius: '50%',
                            display: 'inline-block',
                            animation: `explainStreamPulse 1.1s ${d * 0.16}s ease-in-out infinite`,
                          }} />
                        ))}
                      </div>
                      <style>{`
                        @keyframes explainStreamPulse {
                          0%, 100% { background: #ffffff; opacity: 0.35; transform: scale(0.7); box-shadow: none; }
                          50%      { background: #b078ff; opacity: 1;    transform: scale(1.15); box-shadow: 0 0 8px rgba(176,120,255,0.7); }
                        }
                      `}</style>
                    </div>
                  )
                ) : (
                  <div style={S.boardContent}>
                    {/* ── Right board lines — notes accumulate across questions; ── */}
                    {/* ── each new question starts with its own divider below.   ── */}
                    {explainLines.map((line, i) => {
                      const pct        = explainClipPcts[i] ?? 0
                      const isText     = !!line.isText
                      const isHeading  = !!line.isHeading
                      const isWriting  = line.kind === 'writing'
                      const isNote     = line.kind === 'annotation'
                      const annotation = explainAnnotations[explainLineIds[i]]

                      if (line.kind === 'spacer') {
                        return <div key={i} aria-hidden="true" style={{ width: '100%', height: 18 }} />
                      }

                      if (line.kind === 'divider') {
                        return (
                          <div key={i} style={{
                            opacity:    i < explainVisibleCount ? 1 : 0,
                            transition: 'opacity 0.25s ease',
                            width:      '100%',
                            marginTop:  i === 0 ? 0 : 20,
                            paddingTop: i === 0 ? 0 : 14,
                            borderTop:  i === 0 ? 'none' : '1px solid rgba(185,120,255,0.16)',
                          }}>
                            <div style={{
                              fontSize: 10.5, fontWeight: 600, letterSpacing: '0.1em',
                              textTransform: 'uppercase', color: 'rgba(185,120,255,0.55)',
                            }}>
                              Q · {line.question}
                            </div>
                          </div>
                        )
                      }

                      return (
                        <div key={i} style={{
                          opacity: i < explainVisibleCount ? 1 : 0,
                          transition: 'opacity 0.25s ease',
                          width: '100%', display: 'flex', justifyContent: 'flex-start',
                        }}>
                          <div style={{
                            fontSize:      isNote ? 13 : 15,
                            color:         mode.text || '#e2f4ff',
                            textShadow:    `0 0 12px ${(mode.text || '#e2f4ff')}44`,
                            lineHeight:    isText ? 1.58 : 0.2,
                            margin:        0,
                            padding:       isText ? (isHeading ? '10px 0 2px' : '5px 0') : '5px 0px',
                            userSelect:    isText ? 'text' : 'none',
                            display:       annotation ? 'inline-block' : (isText ? 'block' : 'inline-block'),
                            maxWidth:      isText ? '100%' : 'none',
                            width:         annotation ? 'auto' : (isText ? '100%' : 'auto'),
                            textAlign:     'left',
                            letterSpacing: isHeading ? '0.12em' : '0.01em',
                            fontWeight:    isText && !isHeading ? 500 : undefined,
                            fontStyle:     isNote ? 'italic' : 'normal',
                            opacity:       isNote ? 0.75 : 1,
                            whiteSpace:    isText ? 'normal' : 'nowrap',
                            wordBreak:     'break-word',
                            clipPath:      `inset(0 ${100 - pct}% 0 0)`,
                            // Purple accent for right-board annotations to
                            // visually distinguish Q&A marks from lesson marks.
                            background:         annotation === 'highlight' ? 'rgba(185,120,255,0.14)' : 'transparent',
                            borderRadius:       annotation === 'highlight' ? 4 : (annotation === 'circle' ? 6 : 0),
                            textDecoration:     annotation === 'underline' ? 'underline' : 'none',
                            textDecorationColor: annotation === 'underline' ? 'rgba(185,120,255,0.7)' : 'transparent',
                            outline:            annotation === 'circle' ? '2px solid rgb(255, 255, 255)' : 'none',
                            outlineOffset:      annotation === 'circle' ? 4 : 0,
                            boxShadow:          annotation === 'circle' ? '0 0 10px rgb(255, 255, 255)' : 'none',
                          }}
                            dangerouslySetInnerHTML={{ __html: line.html + (isWriting ? '<span style="display:inline-block;width:1.5px;height:0.9em;background:currentColor;vertical-align:text-bottom;margin-left:2px;animation:blink 0.75s ease-in-out infinite alternate"></span>' : '') }}
                          />
                        </div>
                      )
                    })}

                    {/* Loading dots while SSE is still running and content is arriving */}
                    {explainVisible && explainLoading && explainLines.length > 0 && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '10px 0', opacity: 0.4 }}>
                        {[0, 1, 2].map(d => (
                          <span key={d} style={{
                            width: 3, height: 3, borderRadius: '50%', background: 'rgba(185,120,255,0.8)',
                            display: 'inline-block', animation: `dotBlink 1.2s ${d * 0.2}s ease-in-out infinite`,
                          }} />
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
            {/* ── end right panel — follow-up input migrated out of the board,
                 see the dedicated Q&A input area below the split chalkboard ── */}

          </div>
          {/* ── end split chalkboard ──────────────────────────────────── */}

          {/* ── Raised hand — persistent, deliberately visible whether up or
               down so its state is never ambiguous. Hidden alongside the
               other input controls during AWAIT_RESPONSE / active Q&A, same
               as everything else in this row. ─────────────────────────── */}
          {sourceMode === 'lesson' && !isAwaitingPractice && !explainVisible && (playing || handState !== 'idle') && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 10 }}>
              <button
                onClick={handleRaiseHand}
                disabled={handState === 'active'}
                title={
                  handState === 'idle'          ? 'Raise your hand to ask something'
                  : handState === 'raised'       ? 'Hand up — tap to lower it'
                  : handState === 'acknowledged' ? 'Teacher noticed — tap to lower it'
                  :                                 'Your turn — type below'
                }
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  width: 42, height: 42, borderRadius: '50%', flexShrink: 0,
                  cursor: handState === 'active' ? 'default' : 'pointer',
                  background:
                    handState === 'active'       ? 'rgba(255,184,92,0.22)'
                    : handState === 'acknowledged' ? 'rgba(255,184,92,0.16)'
                    : handState === 'raised'       ? 'rgba(255,184,92,0.12)'
                    :                                 'transparent',
                  border: `1px solid ${handState === 'idle' ? 'rgba(226,244,255,0.15)' : 'rgba(255,184,92,0.45)'}`,
                  color: handState === 'idle' ? 'rgba(226,244,255,0.45)' : '#ffb85c',
                  transition: 'background 0.25s ease, border-color 0.25s ease, color 0.25s ease',
                  animation: (handState === 'raised' || handState === 'acknowledged')
                    ? 'stagePulse 1.6s ease-in-out infinite' : 'none',
                }}
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 11V6a2 2 0 0 1 4 0v5"></path>
                  <path d="M13 10.5V4a2 2 0 0 1 4 0v9"></path>
                  <path d="M17 11.5V7a2 2 0 0 1 4 0v7c0 4-3 8-8 8h-1c-4 0-6-2-7.5-5L2.7 13.1a1.7 1.7 0 0 1 2.6-2.2L7 13"></path>
                </svg>
              </button>

              <span style={{
                fontFamily: "'Crimson Pro', Georgia, serif",
                fontSize: 12, letterSpacing: '0.02em',
                color: handState === 'idle' ? 'rgba(226,244,255,0.35)' : '#ffb85c',
                transition: 'color 0.25s ease',
              }}>
                {
                  handState === 'idle'          ? 'Raise hand to ask a question'
                  : handState === 'raised'       ? 'Hand raised — waiting for the teacher to notice…'
                  : handState === 'acknowledged' ? 'Noted — pausing at a good stopping point…'
                  :                                 'Your turn — type your question below'
                }
              </span>
            </div>
          )}

          {handState === 'active' && sourceMode === 'lesson' && (
            <div style={{
              marginTop: 10, padding: '8px 10px 8px 16px', borderRadius: 8,
              background: 'rgba(255,184,92,0.10)', border: '1px solid rgba(255,184,92,0.35)',
              display: 'flex', alignItems: 'center', gap: 10,
            }}>
              <input
                type="text"
                autoFocus
                value={handQuestionInput}
                onChange={e => setHandQuestionInput(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') { e.preventDefault(); handleHandTurnSubmit() }
                }}
                placeholder="What's your question?"
                style={{
                  flex: 1, background: 'transparent', border: 'none', outline: 'none',
                  color: 'rgba(226,244,255,0.90)',
                  fontFamily: "'Crimson Pro', Georgia, serif",
                  fontSize: 15, padding: '6px 2px',
                }}
              />
              <button
                onClick={handleHandTurnSubmit}
                style={{
                  background: 'none', border: 'none', color: '#ffb85c',
                  cursor: 'pointer', fontSize: 12, fontWeight: 700,
                  letterSpacing: '0.08em', padding: '6px 10px',
                  flexShrink: 0, whiteSpace: 'nowrap',
                }}
                title="Ask"
              >
                ASK →
              </button>
            </div>
          )}

          {isAwaitingPractice && handState === 'idle' && sourceMode === 'lesson' && (
            <div style={{
              marginTop: 10, padding: '8px 10px 8px 16px', borderRadius: 8,
              background: luminaBgColor, border: `1px solid ${luminaBorderColor}`,
              display: 'flex', alignItems: 'center', gap: 10,
            }}>
              <input
                type="text"
                autoFocus
                value={practiceInput}
                onChange={e => setPracticeInput(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') { e.preventDefault(); handlePracticeSubmit() }
                }}
                placeholder={practicePrompt || 'Type your answer here…'}
                style={{
                  flex: 1, background: 'transparent', border: 'none', outline: 'none',
                  color: 'rgba(226,244,255,0.90)',
                  fontFamily: "'Crimson Pro', Georgia, serif",
                  fontSize: 15, padding: '6px 2px',
                }}
              />
              <button
                onClick={handlePracticeSubmit}
                style={{
                  background: 'none', border: 'none', color: luminaLabelColor,
                  cursor: 'pointer', fontSize: 12, fontWeight: 700,
                  letterSpacing: '0.08em', padding: '6px 10px',
                  flexShrink: 0, whiteSpace: 'nowrap',
                }}
                title="Submit attempt"
              >
                SUBMIT →
              </button>
            </div>
          )}

          {/* ── Q&A Explanations follow-up — migrated out of the right board
               panel to live here as its own dedicated input area, same
               pattern as the hand-raise and practice-attempt boxes above.
               Shown whenever the Explain panel is open and waiting on the
               learner (initial question already sent, or a follow-up after
               ANSWER_COMPLETE). Deliberately gated on !explainLoading —
               explainLoading flips true the instant a question is sent and
               only flips back false on LEARNER_CHECKPOINT, ANSWER_COMPLETE,
               or ERROR, i.e. the genuine "awaiting response" moments. This
               keeps the box hidden for the whole time an answer is being
               generated/streamed, not just while the panel is open. ────── */}
          {explainVisible && !explainLoading && sourceMode === 'lesson' && (
            <div style={{
              marginTop: 10, padding: '8px 10px 8px 16px', borderRadius: 8,
              background: 'rgba(185,120,255,0.10)', border: '1px solid rgba(185,120,255,0.35)',
              display: 'flex', alignItems: 'center', gap: 10,
            }}>
              <input
                type="text"
                autoFocus
                value={explainInput}
                onChange={e => setExplainInput(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter' && !explainLoading) {
                    const v = explainInput.trim()
                    if (v) { setExplainInput(''); handleExplainQuestion(v) }
                  }
                }}
                placeholder={explainLoading ? 'Explaining…' : (explainPrompt || 'Got it / Still confused about…')}
                disabled={explainLoading}
                style={{
                  flex: 1, background: 'transparent', border: 'none', outline: 'none',
                  color: 'rgba(226,244,255,0.90)',
                  fontFamily: "'Crimson Pro', Georgia, serif",
                  fontSize: 15, padding: '6px 2px',
                  opacity: explainLoading ? 0.5 : 1,
                }}
              />
              <button
                onClick={() => {
                  const v = explainInput.trim()
                  if (v && !explainLoading) { setExplainInput(''); handleExplainQuestion(v) }
                }}
                disabled={!explainInput.trim() || explainLoading}
                style={{
                  background: 'none', border: 'none',
                  color: explainInput.trim() && !explainLoading ? 'rgba(185,120,255,0.85)' : 'rgba(226,244,255,0.12)',
                  cursor: explainInput.trim() && !explainLoading ? 'pointer' : 'default',
                  fontSize: 12, fontWeight: 700,
                  letterSpacing: '0.08em', padding: '6px 10px',
                  flexShrink: 0, whiteSpace: 'nowrap',
                }}
                title="Send"
              >
                SEND →
              </button>
            </div>
          )}

          {aiExplanation.length > 0 && visibleExplanations > 0 && (
            <div style={S.explanationBlock}>
              <div style={S.explanationHead}>
                <span style={S.explanationTitle}>
                  {sourceMode === 'lesson' ? 'Lesson Notes' : 'AI Instructor Reasoning'}
                </span>
                <button
                  onClick={() => { setAiExplanation([]); setVisibleExplanations(0) }}
                  style={{ ...S.explanationClose, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                  title="Dismiss"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                </button>
              </div>
              <div ref={explanationRef} style={S.explanationBody}>
                {aiExplanation.slice(0, visibleExplanations).map((line, i) => (
                  <div key={i} style={{ animation: 'slideFadeIn 0.35s ease-out forwards' }}>
                    <p style={S.explanationText}>
                      <span style={S.explanationStep}>STEP {String(i + 1).padStart(2, '0')}</span>
                      {line}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

  
        </main>

        <aside style={S.sidebar}>
          <div style={S.section}>
            {hasCourse ? (
              <>
                <div style={S.labelRow}>
                  <span style={S.label}>Course Plan</span>
                  {courseData?.courseDetails?.topic && (
                    <span style={S.courseTopicEllipsis}>{courseData.courseDetails.topic}</span>
                  )}
                </div>

                {courseSections.map((section) => {
                  const isOpen     = openChapter === section.chapterId
                  const totalItems = section.items.length
                  const doneCount  = section.items.filter(it => completedLessons.has(it.globalIndex)).length
                  return (
                    <div key={section.chapterId} style={S.chapterWrap}>
                      <button
                        onClick={() => setOpenChapter(isOpen ? null : section.chapterId)}
                        style={S.catBtn}
                      >
                        <span style={S.catTitle}>{section.category}</span>
                        <span style={S.catProgress}>{doneCount}/{totalItems}</span>
                        <span style={{ ...S.catArrow, display: 'inline-flex' }}>
                          {isOpen
                            ? <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="18 15 12 9 6 15"></polyline></svg>
                            : <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>
                          }
                        </span>
                      </button>

                      {isOpen && section.items.map((item) => {
                        const unlocked   = isLessonUnlocked(item.globalIndex)
                        const isComplete = completedLessons.has(item.globalIndex)
                        const isNext     = !isComplete && unlocked
                        const isActive   = currentLesson?.globalIndex === item.globalIndex && (loadingStage !== null || playing)
                        return (
                          <button
                            key={item.globalIndex}
                            className="si-social"
                            onClick={() => unlocked && !isActive && handleLessonClick(item)}
                            disabled={!unlocked || isActive}
                            title={
                              isActive   ? 'Loading…'
                              : isComplete ? 'Completed — click to revisit'
                              : isNext     ? 'Up next — click to start'
                              :              'Complete the previous lesson first'
                            }
                            style={{
                              ...S.presetBtn,
                              color: isActive ? '#63c8ff'
                                : isComplete ? 'rgba(226,244,255,0.4)'
                                : isNext     ? '#63c8ff'
                                :              'rgba(226,244,255,0.2)',
                              borderColor: (isActive || isNext) ? 'rgba(99,200,255,0.3)' : 'rgba(226,244,255,0.05)',
                              background:  (isActive || isNext) ? 'rgba(99,200,255,0.08)' : 'transparent',
                              cursor: (unlocked && !isActive) ? 'pointer' : 'not-allowed',
                              textDecoration: isComplete ? 'line-through' : 'none',
                              opacity: isActive ? 0.7 : 1,
                            }}
                          >
                            <span style={{ fontSize: 10, flexShrink: 0, display: 'flex', alignItems: 'center' }}>
                              {isActive
                                ? <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ animation: 'spin 2s linear infinite' }}><path d="M21 2v6h-6"></path><path d="M3 12a9 9 0 0 1 15-6.7L21 8"></path><path d="M3 22v-6h6"></path><path d="M21 12a9 9 0 0 1-15 6.7L3 16"></path></svg>
                                : isComplete ? <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                                : isNext     ? <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                                :               <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
                              }
                            </span>
                            <span style={S.presetLabel}>{item.label}</span>
                          </button>
                        )
                      })}
                    </div>
                  )
                })}
              </>
            ) : (
              <>
                <div style={S.labelRow}><span style={S.label}>Presets</span></div>
                {PRESETS.map(cat => (
                  <div key={cat.category} style={S.chapterWrap}>
                    <button
                      onClick={() => setOpenChapter(openChapter === cat.category ? null : cat.category)}
                      style={S.catBtn}
                    >
                      <span style={S.catTitle}>{cat.category}</span>
                      <span style={{ ...S.catArrow, display: 'inline-flex' }}>
                        {openChapter === cat.category
                          ? <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="18 15 12 9 6 15"></polyline></svg>
                          : <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>
                        }
                      </span>
                    </button>
                    {openChapter === cat.category && cat.items.map(item => (
                      <button
                        key={item.label}
                        className="si-social"
                        onClick={() => handlePreset(item.latex)}
                        style={S.presetBtn}
                      >
                        <span style={S.presetLabel}>{item.label}</span>
                      </button>
                    ))}
                  </div>
                ))}
              </>
            )}
          </div>
        </aside>
      </div>
    </div>
  )
}