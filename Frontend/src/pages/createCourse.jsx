import React, { useState, useEffect, useRef, useCallback } from 'react'
import { S } from '../styles/createCourseStyles'
import '../styles/createCourse.css';
import { RATINGS, TYPE_COLORS, MAX_PDF_BYTES, MAX_PDF_MB } from '../constants/courseConstants';
import { uploadPdf, fetchCoursePlan, fetchPrerequisites} from '../utils/createCourseHelpers';

import { Spinner, ErrorIcon, UploadSpinner } from '../components/sharedComponents';
import { PARTICLES } from '../constants/floatingParticles';

// Component 
export default function CreateCourse({ onNavigate, onBack }) {
  const [mounted, setMounted] = useState(false)
  const [step,    setStep]    = useState(1)

  // Step 1 state 
  const [topic,    setTopic]    = useState('')
  const [goal,     setGoal]     = useState('')
  // noSource=true  → AI path (no PDF)
  // noSource=false → PDF path (upload required)
  const [noSource, setNoSource] = useState(false)

  // PDF upload state
  const [pdfFile,       setPdfFile]       = useState(null)   // File object
  const [pdfError,      setPdfError]      = useState(null)   // client-side file validation error
  const [pdfLoading,    setPdfLoading]    = useState(false)  // /extract-pdf in flight
  const [sourceSummary, setSourceSummary] = useState(null)   // stored from /extract-pdf response
  const [pdfMeta,       setPdfMeta]       = useState(null)   // extraction_meta from /extract-pdf
  const [isDragging,    setIsDragging]    = useState(false)  // drag-over visual state

  const fileInputRef = useRef(null)

  // Step 2 state 
  const [prerequisites, setPrerequisites] = useState([])
  const [ratings,       setRatings]       = useState({})

  // Step 3 / API state
  const [loading,          setLoading]          = useState(false)
  const [apiError,         setApiError]         = useState(null)
  const [courseData,       setCourseData]        = useState(null)
  const [expandedChapters, setExpandedChapters] = useState({})

  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 40)
    return () => clearTimeout(t)
  }, [])

  // PDF file validation 
  const validateAndSetFile = useCallback((file) => {
    setPdfError(null)
    if (!file) return

    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      setPdfError('Only PDF files are accepted.')
      return
    }
    if (file.size > MAX_PDF_BYTES) {
      setPdfError(`File exceeds the ${MAX_PDF_MB} MB limit (${(file.size / 1024 / 1024).toFixed(1)} MB).`)
      return
    }

    setPdfFile(file)
    // Clear any previous extraction result when a new file is selected
    setSourceSummary(null)
    setPdfMeta(null)
  }, [])

  // Drag-and-drop handlers
  const onDragOver = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    if (!noSource) setIsDragging(true)
  }, [noSource])

  const onDragLeave = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }, [])

  const onDrop = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
    if (noSource) return
    const file = e.dataTransfer.files?.[0]
    if (file) validateAndSetFile(file)
  }, [noSource, validateAndSetFile])

  // Toggle: AI vs PDF mode 
  const handleToggleNoSource = (checked) => {
    setNoSource(checked)
    if (checked) {
      // Switching to AI mode — clear PDF state
      setPdfFile(null)
      setPdfError(null)
      setSourceSummary(null)
      setPdfMeta(null)
    }
  }

  // Step 1 → 2 
  // PDF path: upload → extract → /prerequisites (with source_summary)
  // AI  path: /prerequisites (topic + goal only)
  const handleNextToStep2 = async (e) => {
    e.preventDefault()
    if (!topic.trim() || !goal.trim()) return

    // PDF path guard: a file must be selected
    if (!noSource && !pdfFile) {
      setPdfError('Please select a PDF file, or choose "Generate from scratch (AI)" below.')
      return
    }

    setApiError(null)
    let resolvedSummary = sourceSummary  // may already be set from a previous upload

    // ── PDF path: extract if we have a fresh file without a cached summary ───
    if (!noSource && pdfFile && !sourceSummary) {
      setPdfLoading(true)
      try {
        const extracted = await uploadPdf(pdfFile)

        // Cache the summary and metadata in state
        setSourceSummary(extracted.source_summary)
        setPdfMeta(extracted.extraction_meta)
        resolvedSummary = extracted.source_summary

        // Pre-fill topic from the PDF's inferred title if the user left it blank
        if (!topic.trim() && extracted.extraction_meta?.inferred_title) {
          setTopic(extracted.extraction_meta.inferred_title)
        }
      } catch (err) {
        setPdfError(err.message)
        setPdfLoading(false)
        return
      } finally {
        setPdfLoading(false)
      }
    }

    // ── Fetch prerequisites (both paths) ──────────────────────────────────────
    setLoading(true)
    try {
      const prereqData = await fetchPrerequisites({
        topic,
        goal,
        sourceSummary: resolvedSummary,   // null on AI path, string on PDF path
      })
      setPrerequisites(prereqData)

      // Pre-fill all prerequisite ratings to "Familiar" (2)
      const initialRatings = {}
      prereqData.forEach(p => { initialRatings[p.id] = 2 })
      setRatings(initialRatings)
      setStep(2)
    } catch (err) {
      setApiError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // ── Step 2 → 3 ─────────────────────────────────────────────────────────────
  const handleNextToStep3 = async (e) => {
    e.preventDefault()
    setApiError(null)
    setLoading(true)
    setStep(3)  // show Step 3 skeleton immediately

    try {
      const data = await fetchCoursePlan({
        topic,
        goal,
        noSource,
        ratings,
        sourceSummary,  // null on AI path, string on PDF path
      })
      setCourseData(data)
    } catch (err) {
      setApiError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // ── Step 3 retry ───────────────────────────────────────────────────────────
  const handleRetry = () => {
    setApiError(null)
    setLoading(true)
    fetchCoursePlan({ topic, goal, noSource, ratings, sourceSummary })
      .then(setCourseData)
      .catch(err => setApiError(err.message))
      .finally(() => setLoading(false))
  }

  const toggleChapter = (id) =>
    setExpandedChapters(prev => ({ ...prev, [id]: !prev[id] }))

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!coursePlan) return

    // Weak areas = prerequisites the student rated <= 2 (Novice / Familiar).
    // Passed to LessonPage so the lesson engine deepens revision for these topics.
    const weakAreas = prerequisites
      .filter(p => (ratings[p.id] ?? 2) <= 2)
      .map(p => p.label)

    // Full payload App.jsx stores and passes to LessonPage as courseData prop.
    const coursePayload = {
      coursePlan:    coursePlan,      // { course_name, estimated_total_hours, chapters[] }
      courseDetails: summaryDetails,  // { topic, goal, source }
      prerequisites: prerequisites,  // [{ id, label }]
      ratings:       ratings,        // { [prereqId]: 1|2|3|4 }
      weakAreas:     weakAreas,      // string[] — labels rated <= 2
    }

    onNavigate('lesson', coursePayload)
  }

  // ── Step 3 display helpers ─────────────────────────────────────────────────
  const summaryDetails = courseData?.course_details ?? {
    topic,
    goal,
    source: noSource ? 'AI Generated' : 'PDF Uploaded',
  }
  const summaryPrereqs = courseData?.prerequisites ?? {}
  const coursePlan     = courseData?.course_plan ?? null

  // ── Upload zone state text ─────────────────────────────────────────────────
  const isUploading     = !noSource && pdfLoading
  const uploadDisabled  = noSource || pdfLoading
  const step1Busy       = loading || pdfLoading

  // What the Continue button is waiting for
  const pdfPathReady = noSource || !!pdfFile
  const continueDisabled = step1Busy || !topic.trim() || !goal.trim() || !pdfPathReady

  return (
    <div style={S.root}>

      {/* Background layers */}
      <div style={S.mesh} aria-hidden />
      <div style={S.grid} aria-hidden />
      <div style={S.particleLayer} aria-hidden>
        {PARTICLES.map((p, i) => (
          <span key={i} style={{
            position: 'absolute', left: p.x, top: p.y, fontSize: p.size,
            color: '#63c8ff', fontFamily: '"Crimson Pro", Georgia, serif',
            opacity: 0.04, pointerEvents: 'none',
            animation: `floatUp ${p.dur} ease-in-out ${p.delay} infinite`,
          }}>{p.char}</span>
        ))}
      </div>

      <button onClick={() => onBack('home')} style={S.backLink}>← Back to Dashboard</button>

      {/* ── Card ─────────────────────────────────────────────────────────────── */}
      <div style={{
        ...S.card,
        maxWidth: step === 3 ? 640 : 500,
        opacity: mounted ? 1 : 0,
        transform: mounted ? 'translateY(0)' : 'translateY(30px)',
        transition: 'all 0.5s cubic-bezier(0.16, 1, 0.3, 1)',
      }}>

        {/* Progress bar */}
        <div style={S.stepBar}>
          <div style={S.stepTrack}>
            <div style={{
              ...S.stepFill,
              width: step === 1 ? '33.3%' : step === 2 ? '66.6%' : '100%',
              transition: 'width 0.6s cubic-bezier(0.16, 1, 0.3, 1)',
            }} />
          </div>
          <div style={S.stepLabels}>
            {[['01 · Details', 1], ['02 · Prerequisites', 2], ['03 · Plan', 3]].map(([label, n]) => (
              <React.Fragment key={n}>
                <span style={{ ...S.stepLabelText, color: step >= n ? '#63c8ff' : 'rgba(226,244,255,0.28)' }}>
                  {label}
                </span>
                {n < 3 && <span style={{ color: 'rgba(226,244,255,0.16)', fontSize: 10 }}>——</span>}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Form header */}
        <div style={S.formHead}>
          {step === 1 && (
            <div style={{ animation: 'stepSlide 0.4s ease forwards' }}>
              <h1 style={S.formH1}>Design your course</h1>
              <p style={S.formSub}>Tell Lumina what you want to learn and how.</p>
            </div>
          )}
          {step === 2 && (
            <div style={{ animation: 'stepSlide 0.4s ease forwards' }}>
              <h1 style={S.formH1}>Assess prerequisite strengths</h1>
              <p style={S.formSub}>
                Rate your current foundation for{' '}
                <strong style={{ color: '#fff' }}>{topic}</strong> to tailor the curriculum.
              </p>
            </div>
          )}
          {step === 3 && (
            <div style={{ animation: 'stepSlide 0.4s ease forwards' }}>
              <h1 style={S.formH1}>Review &amp; Curriculum</h1>
              <p style={S.formSub}>
                {loading ? 'Lumina is building your personalised plan…' : 'Your personalised course structure is ready.'}
              </p>
            </div>
          )}
        </div>

        {/* Global errors (Steps 1 & 2) */}
        {apiError && step !== 3 && (
          <div style={S.errorBox}>
            <ErrorIcon />
            <span>{apiError}</span>
          </div>
        )}

        {/* ══ STEP 1 ══════════════════════════════════════════════════════════ */}
        {step === 1 && (
          <form onSubmit={handleNextToStep2} style={S.form}>

            {/* Course Topic */}
            <div style={S.field}>
              <label style={S.label}>Course Topic</label>
              <input
                className="cc-input"
                placeholder="e.g. Grade 12 Mathematics, Quantum Mechanics…"
                value={topic}
                onChange={e => setTopic(e.target.value)}
                required
                autoFocus
              />
              {pdfMeta && (
                <div style={S.metaHint}>
                  <span style={{ opacity: 0.5 }}>Detected from PDF:</span>{' '}
                  {pdfMeta.inferred_subject} · {pdfMeta.inferred_grade} · {pdfMeta.total_pages} pages
                </div>
              )}
            </div>

            {/* Learning Goal */}
            <div style={S.field}>
              <label style={S.label}>Primary Goal</label>
              <input
                className="cc-input"
                placeholder="e.g. Pass my finals next month, understand architectural application…"
                value={goal}
                onChange={e => setGoal(e.target.value)}
                required
              />
            </div>

            {/* PDF upload zone */}
            <div style={S.field}>
              <label style={S.label}>Source Material (PDF)</label>

              {/* Hidden real file input */}
              <input
                ref={fileInputRef}
                type="file"
                accept="application/pdf,.pdf"
                style={{ display: 'none' }}
                onChange={e => validateAndSetFile(e.target.files?.[0])}
              />

              {/* Drop zone */}
              <div
                className={[
                  'cc-upload',
                  uploadDisabled    ? 'disabled'    : '',
                  isDragging        ? 'drag-over'   : '',
                  isUploading       ? 'is-uploading': '',
                  pdfError          ? 'has-error'   : '',
                  pdfFile && !pdfError && !isUploading ? 'has-file' : '',
                ].filter(Boolean).join(' ')}
                onClick={() => !uploadDisabled && fileInputRef.current?.click()}
                onDragOver={onDragOver}
                onDragLeave={onDragLeave}
                onDrop={onDrop}
                role="button"
                aria-label="Upload PDF"
              >
                {/* State-driven icon */}
                {isUploading ? (
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 }}>
                    <UploadSpinner />
                    <div style={{ fontSize: 13, color: '#63c8ff', fontWeight: 600 }}>
                      Extracting content…
                    </div>
                    <div style={{ fontSize: 12, color: 'rgba(226,244,255,0.4)' }}>
                      PyMuPDF → chunking → Lumina lesson generator
                    </div>
                  </div>
                ) : pdfFile && !pdfError ? (
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
                    {/* PDF file icon */}
                    <div style={S.fileIconWrap}>
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#63c8ff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <polyline points="14 2 14 8 20 8"/>
                        <line x1="9" y1="13" x2="15" y2="13"/>
                        <line x1="9" y1="17" x2="15" y2="17"/>
                      </svg>
                    </div>
                    <div style={{ fontSize: 14, color: '#ffffff', fontWeight: 700 }}>
                      {pdfFile.name}
                    </div>
                    <div style={{ fontSize: 12, color: 'rgba(226,244,255,0.45)', fontFamily: '"DM Mono", monospace' }}>
                      {(pdfFile.size / 1024 / 1024).toFixed(2)} MB
                      {sourceSummary && <span style={{ color: '#34d399', marginLeft: 8 }}>✓ Extracted</span>}
                    </div>
                    <button
                      type="button"
                      onClick={ev => { ev.stopPropagation(); setPdfFile(null); setSourceSummary(null); setPdfMeta(null); setPdfError(null) }}
                      style={S.clearFileBtn}
                    >
                      Remove
                    </button>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke={pdfError ? '#fb7185' : '#63c8ff'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.9 }}>
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                      <polyline points="17 8 12 3 7 8"/>
                      <line x1="12" y1="3" x2="12" y2="15"/>
                    </svg>
                    <div style={{ fontSize: 14, color: pdfError ? '#fb7185' : '#ffffff', fontWeight: 600 }}>
                      {isDragging ? 'Drop PDF here' : 'Click or drag a syllabus / PDF here'}
                    </div>
                    <div style={{ fontSize: 12, color: 'rgba(226,244,255,0.4)' }}>
                      Maximum file size {MAX_PDF_MB} MB
                    </div>
                  </div>
                )}
              </div>

              {/* Client-side file validation error */}
              {pdfError && (
                <div style={S.fieldError}>
                  <ErrorIcon size={14} /> {pdfError}
                </div>
              )}

              {/* AI mode toggle */}
              <label style={S.checkboxRow}>
                <div style={{
                  ...S.customCheck,
                  background:  noSource ? '#63c8ff' : 'transparent',
                  borderColor: noSource ? '#63c8ff' : 'rgba(255,255,255,0.2)',
                }}>
                  {noSource && (
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#050914" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12"/>
                    </svg>
                  )}
                </div>
                <input
                  type="checkbox"
                  checked={noSource}
                  onChange={e => handleToggleNoSource(e.target.checked)}
                  style={{ display: 'none' }}
                />
                <span style={{ fontSize: 14, color: 'rgba(226,244,255,0.7)', userSelect: 'none' }}>
                  Generate curriculum from scratch (AI)
                </span>
              </label>
            </div>

            <button
              type="submit"
              className="next-btn"
              disabled={continueDisabled}
              style={{ ...S.submitBtn, opacity: continueDisabled ? 0.45 : 1 }}
            >
              {pdfLoading
                ? <><UploadSpinner small /> Extracting PDF…</>
                : loading
                  ? <><Spinner /> Mapping Requirements…</>
                  : <> Course Plan<span style={{ fontSize: 18 }}>→</span></>
              }
            </button>
          </form>
        )}

        {/* ══ STEP 2 ══════════════════════════════════════════════════════════ */}
        {step === 2 && (
          <form onSubmit={handleNextToStep3} style={{ ...S.form, animation: 'stepSlide 0.4s ease forwards' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginBottom: 10 }}>
              {prerequisites.map(req => (
                <div key={req.id} style={S.reqRow}>
                  <div style={S.reqLabel}>{req.label}</div>
                  <div style={S.ratingGrid}>
                    {RATINGS.map(r => {
                      const on = ratings[req.id] === r.id
                      return (
                        <button
                          key={r.id} type="button" className="cc-rating"
                          onClick={() => setRatings(p => ({ ...p, [req.id]: r.id }))}
                          style={{
                            ...S.ratingBtn,
                            borderColor: on ? '#63c8ff' : 'rgba(255,255,255,0.1)',
                            background:  on ? 'rgba(99,200,255,0.15)' : 'rgba(255,255,255,0.02)',
                            color:       on ? '#ffffff' : 'rgba(226,244,255,0.5)',
                          }}
                        >
                          {r.label}
                        </button>
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>

            <button type="submit" className="next-btn" style={{ ...S.submitBtn, marginTop: 10 }}>
              Finalise Course Plan <span style={{ fontSize: 18 }}>→</span>
            </button>
            <button type="button" onClick={() => setStep(1)} style={S.backStepBtn}>
              ← Back to Details
            </button>
          </form>
        )}

        {/* ══ STEP 3 ══════════════════════════════════════════════════════════ */}
        {step === 3 && (
          <form onSubmit={handleSubmit} style={{ ...S.form, animation: 'stepSlide 0.4s ease forwards' }}>

            {/* Summaries */}
            <div style={S.summaryGrid}>
              <div style={S.summaryBox}>
                <div style={S.summaryTitle}>Course Details</div>
                <div style={S.summaryItem}>
                  <span>Topic:</span>
                  <strong>{summaryDetails.topic || 'Untitled'}</strong>
                </div>
                <div style={S.summaryItem}>
                  <span>Goal:</span>
                  <strong style={{ maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {summaryDetails.goal || '—'}
                  </strong>
                </div>
                <div style={S.summaryItem}>
                  <span>Source:</span>
                  <strong>{summaryDetails.source || '—'}</strong>
                </div>
                {pdfMeta && (
                  <div style={S.summaryItem}>
                    <span>Pages:</span>
                    <strong>{pdfMeta.total_pages}</strong>
                  </div>
                )}
              </div>

              <div style={S.summaryBox}>
                <div style={S.summaryTitle}>Foundation Strengths</div>
                {prerequisites.map(req => {
                  const displayVal =
                    summaryPrereqs[req.id] ||
                    RATINGS.find(r => r.id === ratings[req.id])?.label ||
                    'Familiar'
                  return (
                    <div key={req.id} style={S.summaryItem}>
                      <span>{req.label.replace(' Strength', '')}:</span>
                      <strong>{displayVal}</strong>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Error + retry */}
            {apiError && (
              <div style={S.errorBox}>
                <ErrorIcon />
                <span>{apiError}</span>
                <button type="button" onClick={handleRetry} style={S.retryBtn}>
                  Retry
                </button>
              </div>
            )}

            {/* Course plan */}
            <div style={S.curriculumBox}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                <div style={S.summaryTitle}>Course Plan</div>
                {coursePlan && (
                  <div style={{ fontSize: 12, fontFamily: '"DM Mono", monospace', color: 'rgba(226,244,255,0.4)' }}>
                    Total Time: {coursePlan.estimated_total_hours}
                  </div>
                )}
              </div>

              {/* Loading skeleton */}
              {loading && !coursePlan && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 14 }}>
                  {[1, 2, 3, 4].map(i => (
                    <div key={i} style={{
                      display: 'flex', alignItems: 'center', gap: 14,
                      background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)',
                      borderRadius: 12, padding: '14px 16px',
                    }}>
                      <div className="skeleton-line" style={{ width: 32, height: 32, borderRadius: '50%', flexShrink: 0 }} />
                      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}>
                        <div className="skeleton-line" style={{ height: 14, width: `${60 + i * 8}%` }} />
                        <div className="skeleton-line" style={{ height: 10, width: '40%' }} />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Expandable chapters */}
              {coursePlan && (() => {
                // Build a flat global index map so we can enforce the sequential
                // lock rule: lesson at globalIdx N is only enabled when N === 0
                // or the lesson at globalIdx N-1 is completed.
                // completedLessons is managed in LessonPage (DB-wired later).
                // In this review panel all lessons show as "upcoming" — the lock
                // UI lives in Lesson.jsx's course sidebar, not here.
                let globalIdx = -1
                return (
                  <div style={S.curriculumList}>
                    {coursePlan.chapters?.map((ch, idx) => {
                      const chapterKey = ch.id || String(idx)
                      const isExpanded = !!expandedChapters[chapterKey]
                      const colors = TYPE_COLORS[ch.type] || { bg: 'rgba(255,255,255,0.08)', text: '#e2f4ff' }
                      return (
                        <div key={chapterKey} className="curriculum-item" style={S.curriculumWrapper}>
                          <div
                            onClick={() => toggleChapter(chapterKey)}
                            style={S.curriculumItemHeader}
                            className="cc-item-header"
                          >
                            <div style={S.curriculumIcon}>
                              <svg
                                width="14" height="14" viewBox="0 0 24 24"
                                fill="none" stroke="currentColor" strokeWidth="2.5"
                                style={{ transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}
                              >
                                <polyline points="9 18 15 12 9 6"/>
                              </svg>
                            </div>
                            <div style={S.curriculumDetails}>
                              <div style={S.curriculumTitle}>{ch.title}</div>
                              <div style={S.curriculumMeta}>
                                <span style={{ ...S.curriculumBadge, background: colors.bg, color: colors.text }}>
                                  {ch.type}
                                </span>
                                <span>•</span>
                                <span>Est. {ch.estimated_duration}</span>
                                {ch.lessons?.length > 0 && (
                                  <>
                                    <span>•</span>
                                    <span>{ch.lessons.length} Lesson{ch.lessons.length !== 1 ? 's' : ''}</span>
                                  </>
                                )}
                              </div>
                            </div>
                          </div>

                          {isExpanded && ch.lessons && (
                            <div style={S.lessonsDropdown}>
                              {ch.lessons.map((lesson, lIdx) => {
                                globalIdx++
                                const lessonTitle = typeof lesson === 'string' ? lesson : lesson.title
                                // In this review panel lessons are display-only.
                                // The first lesson is shown as "up next", the rest as upcoming.
                                // Full clickability + lock logic lives in Lesson.jsx sidebar.
                                const isFirst = globalIdx === 0
                                return (
                                  <div
                                    key={lIdx}
                                    style={S.lessonRow}
                                    // data-global-index is the wire point for LessonPage
                                    // to look up completion state when DB is connected.
                                    data-global-index={globalIdx}
                                    data-chapter-id={chapterKey}
                                    data-lesson-index={lIdx}
                                  >
                                    <div style={{
                                      ...S.lessonBullet,
                                      background: isFirst ? '#63c8ff' : 'rgba(226,244,255,0.2)',
                                    }} />
                                    <span style={{
                                      ...S.lessonText,
                                      color: isFirst
                                        ? '#e2f4ff'
                                        : 'rgba(226,244,255,0.45)',
                                    }}>
                                      {lessonTitle}
                                    </span>
                                    {isFirst && (
                                      <span style={{
                                        marginLeft: 'auto',
                                        fontSize: 10,
                                        fontFamily: '"DM Mono", monospace',
                                        color: '#63c8ff',
                                        letterSpacing: '0.06em',
                                        flexShrink: 0,
                                      }}>
                                        UP NEXT
                                      </span>
                                    )}
                                  </div>
                                )
                              })}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )
              })()}
            </div>

            <button
              type="submit"
              className="next-btn"
              disabled={loading || !!apiError || !coursePlan}
              style={{ ...S.submitBtn, marginTop: 10, opacity: (loading || !!apiError || !coursePlan) ? 0.45 : 1 }}
            >
              {loading
                ? <><Spinner /> Finalizing course plan…</>
                : <>Confirm &amp; Start Learning <span style={{ fontSize: 18 }}>→</span></>
              }
            </button>

            <button type="button" onClick={() => setStep(2)} style={S.backStepBtn}>
              ← Edit Prerequisites
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
