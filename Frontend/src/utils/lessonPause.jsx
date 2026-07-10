import React, { useState, useRef, useEffect, useCallback } from 'react'
import katex from 'katex'

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
