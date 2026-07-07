export const S = {
root: {
  minHeight: '100vh', width: '100%',
  background: '#070b14', // Match SignIn dark bg
  display: 'flex', flexDirection: 'column',
  position: 'relative', overflow: 'hidden',
  fontFamily: '"Cabinet Grotesk", sans-serif',
  color: '#e2f4ff',
},
mesh: {
  position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0,
  background: `
    radial-gradient(ellipse 70% 60% at 15% 20%, rgba(99,200,255,0.08) 0%, transparent 60%),
    radial-gradient(ellipse 55% 45% at 85% 75%, rgba(120,80,255,0.07) 0%, transparent 60%)
  `,
},
grid: {
  position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0,
  backgroundImage: `
    linear-gradient(rgba(99,200,255,0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(99,200,255,0.025) 1px, transparent 1px)
  `,
  backgroundSize: '52px 52px',
},
particleLayer: { position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0 },

header: {
  height: 72,
  borderBottom: '1px solid rgba(99,200,255,0.1)',
  background: 'rgba(7, 11, 20, 0.65)',
  backdropFilter: 'blur(16px)',
  WebkitBackdropFilter: 'blur(16px)',
  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  padding: '0 32px',
  position: 'relative', zIndex: 10,
},
headerLeft: { display: 'flex', alignItems: 'center', gap: 20 },
backBtn: {
  background: 'none', border: 'none', cursor: 'pointer',
  color: 'rgba(226,244,255,0.55)', fontSize: 13,
  fontFamily: '"DM Mono", monospace', letterSpacing: '0.04em',
  display: 'flex', alignItems: 'center', gap: 6,
  transition: 'color 0.2s', padding: '6px 0',
},
headerDivider: { width: 1, height: 24, background: 'rgba(99,200,255,0.15)' },
headerTitle: {
  fontSize: 16, fontWeight: 700,
  letterSpacing: '-0.01em', color: '#e2f4ff',
},
apiBadge: {
  fontSize: 10, fontFamily: '"DM Mono", monospace', letterSpacing: '0.12em',
  padding: '4px 10px', borderRadius: 20, border: '1px solid',
  marginLeft: 12,
},

layout: { 
  display: 'flex', 
  flex: 1, 
  position: 'relative', 
  zIndex: 2, 
  overflow: 'hidden' 
},

// Aside moved to the right by switching border styling and DOM order
sidebar: {
  width: 280,
  background: 'linear-gradient(160deg, #0e1a2e 0%, #080f1c 100%)',
  borderLeft: '1px solid rgba(99,200,255,0.1)',
  display: 'flex', flexDirection: 'column',
  overflowY: 'auto',
  padding: '32px 24px', gap: 32,
},
section: { display: 'flex', flexDirection: 'column', gap: 14 },
labelRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' },
label: { fontSize: 11, color: 'rgba(226,244,255,0.4)', fontFamily: '"DM Mono", monospace', letterSpacing: '0.08em', textTransform: 'uppercase' },
liveIndicator: { color: '#63c8ff', fontSize: 10, fontFamily: '"DM Mono", monospace', fontWeight: 500 },
courseTopicEllipsis: { fontSize: 10, fontFamily: '"DM Mono", monospace', color: '#63c8ff', opacity: 0.7, maxWidth: 120, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' },

textarea: {
  resize: 'vertical', minHeight: 80,
  fontFamily: '"DM Mono", monospace', fontSize: 13, lineHeight: 1.5,
  padding: '12px 14px', background: 'rgba(7, 11, 20, 0.4)',
},
sideBtnPrimary: {
  width: '100%', padding: '12px', borderRadius: 11, border: 'none',
  fontSize: 14, fontWeight: 700, fontFamily: '"Cabinet Grotesk", sans-serif',
  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
  transition: 'all 0.2s ease',
},
sideBtnSecondary: {
  width: '100%', padding: '10px', borderRadius: 10,
  background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(226,244,255,0.1)',
  color: '#e2f4ff', fontSize: 13, fontWeight: 600,
  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
},
error: { color: '#f06e6e', fontSize: 12, marginTop: 4, fontFamily: '"Cabinet Grotesk", sans-serif' },
divider: { height: 1, background: 'rgba(99,200,255,0.08)', margin: '4px -24px' },

chapterWrap: { display: 'flex', flexDirection: 'column', gap: 6 },
catBtn: {
  display: 'flex', alignItems: 'center', width: '100%',
  padding: '12px 14px', borderRadius: 10,
  background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(99,200,255,0.08)',
  cursor: 'pointer', transition: 'background 0.2s',
},
catTitle: { flex: 1, textAlign: 'left', fontSize: 13, fontWeight: 600, color: '#e2f4ff' },
catProgress: { fontSize: 11, fontFamily: '"DM Mono", monospace', color: 'rgba(226,244,255,0.4)', marginRight: 10 },
catArrow: { fontSize: 10, color: 'rgba(226,244,255,0.3)' },

presetBtn: {
  display: 'flex', alignItems: 'center', gap: 10,
  width: '100%', padding: '10px 14px', borderRadius: 8,
  border: '1px solid transparent',
  fontSize: 13, fontWeight: 500, fontFamily: '"Cabinet Grotesk", sans-serif',
  transition: 'all 0.2s', textAlign: 'left',
},
presetLabel: { flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },

main: { flex: 1, display: 'flex', flexDirection: 'column', padding: '32px', gap: 24, position: 'relative' },

boardShell: {
  flex: 1,
  borderRadius: 22,
  background: 'linear-gradient(160deg, #0c1422 0%, #080e1a 100%)',
  border: '1px solid rgba(99,200,255,0.12)',
  boxShadow: '0 0 0 1px rgba(99,200,255,0.05), 0 32px 90px rgba(0,0,0,0.65), 0 4px 24px rgba(0,0,0,0.4)',
  overflow: 'hidden',
  position: 'relative',
  display: 'flex', flexDirection: 'column',
  maxHeight: 500,
},
boardInner: {
  flex: 1, overflowY: 'auto',
  padding: '40px 48px',
  display: 'flex', flexDirection: 'column',
  // flex-start anchors content to top — prevents top-truncation on scroll-back
  justifyContent: 'flex-start', alignItems: 'flex-start',
},
boardContent: {
  display: 'flex', flexDirection: 'column',
  alignItems: 'flex-start', gap: 1,
  width: '100%',
  position: 'relative', zIndex: 2,
},
emptyBoardState: {
  position: 'absolute', top: '50%', right: '50%', transform: 'translate(-20%, -60%)',
  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16,
  color: 'rgba(99,200,255,0.2)', fontFamily: '"DM Mono", monospace', fontSize: 13, letterSpacing: '0.2em',
  pointerEvents: 'none', userSelect: 'none',
},
emptyIcon: { fontSize: 48, fontFamily: '"Crimson Pro", serif', opacity: 0.5 },
streamingIndicator: {
  position: 'absolute', bottom: 20, right: 24,
  fontSize: 11, fontFamily: '"DM Mono", monospace', letterSpacing: '0.15em',
  color: '#63c8ff', animation: 'blink 1.2s ease-in-out infinite',
},

// Now a static block beneath the board instead of a floating overlay
explanationBlock: {
  background: 'rgba(12, 20, 34, 0.65)',
  border: '1px solid rgba(99,200,255,0.15)',
  borderRadius: 16,
  boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
  display: 'flex', flexDirection: 'column',
  maxHeight: 250,
  flexShrink: 0,
},
explanationHead: {
  padding: '12px 20px', borderBottom: '1px solid rgba(99,200,255,0.1)',
  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
  background: 'rgba(255,255,255,0.02)',
  borderTopLeftRadius: 16, borderTopRightRadius: 16,
},
explanationTitle: { fontSize: 11, fontWeight: 700, fontFamily: '"Cabinet Grotesk", sans-serif', letterSpacing: '0.04em', color: '#63c8ff', textTransform: 'uppercase' },
explanationClose: { background: 'none', border: 'none', color: 'rgba(226,244,255,0.4)', cursor: 'pointer', padding: 4, transition: 'color 0.2s' },
explanationBody: { padding: '16px 20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 14 },
explanationText: {
  margin: 0, fontSize: 15, lineHeight: 1.7,
  color: 'rgba(226,244,255,0.85)', fontFamily: '"Crimson Pro", Georgia, serif',
  borderLeft: '2px solid rgba(99,200,255,0.3)', paddingLeft: 1,
},
explanationStep: { fontSize: 10, fontFamily: '"DM Mono", monospace', color: '#63c8ff', opacity: 0.8, marginRight: 1, letterSpacing: '0.05em' },

controlsContainer: {
  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
  padding: '0 8px',
},
ctrlGroup: { display: 'flex', alignItems: 'center', gap: 16 },
ctrlLabel: { fontSize: 11, fontFamily: '"DM Mono", monospace', letterSpacing: '0.1em', color: 'rgba(226,244,255,0.4)', textTransform: 'uppercase' },
pacingPills: { display: 'flex', background: 'rgba(0,0,0,0.2)', borderRadius: 10, padding: 4, border: '1px solid rgba(255,255,255,0.05)' },
ctrlPill: {
  padding: '6px 14px', borderRadius: 6, border: '1px solid',
  fontSize: 12, fontWeight: 600, fontFamily: '"Cabinet Grotesk", sans-serif',
  cursor: 'pointer', transition: 'all 0.2s ease',
},
actionBtn: {
  padding: '10px 20px', borderRadius: 10,
  background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(226,244,255,0.1)',
  color: '#e2f4ff', fontSize: 13.5, fontWeight: 600,
  display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer',
},
}

export const LOADING_STAGES = [
  { key: 'plan',       icon: <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path><rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect></svg>, label: 'Building lesson plan…' },
  { key: 'anticipate', icon: <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>, label: 'Anticipating questions…' },
  { key: 'session',    icon: <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>, label: 'Initializing classroom…' },
]


// Speed → clip-reveal duration per line (ms).
// Tuned to teacher pacing: Normal ≈ chalk-write for a mid-complexity equation,
// Slow ≈ deliberate step-by-step, Fast ≈ quick review / familiar material.
export const SPEEDS = { Slow: 3500, Normal: 1800, Fast: 600 }

// Speed → server delay (seconds between SSE events) — mirrors SPEEDS / 1000
export const SSE_DELAYS = { Slow: 3.5, Normal: 1.8, Fast: 0.6 }

// src/constants/explainPanelStyles.js

export const EXPLAIN_STYLES = {
  container: {
    flex: '2 1 0',
    minWidth: 0,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  header: {
    flexShrink: 0,
    padding: '10px 16px 6px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderBottom: '1px solid rgba(226,244,255,0.04)',
  },
  headerTitle: {
    fontSize: 9,
    letterSpacing: '0.18em',
    textTransform: 'uppercase',
    transition: 'color 0.4s ease',
  },
  resumeBtn: {
    background: 'none',
    border: 'none',
    color: 'rgba(226,244,255,0.22)',
    fontSize: 10,
    letterSpacing: '0.08em',
    padding: '2px 4px',
    transition: 'color 0.2s ease',
  },
  scrollArea: {
    flex: 1,
    minHeight: 0,
    overflowY: 'auto',
    borderRadius: 0,
    padding: '12px 16px',
  },
  dingState: {
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 14,
    pointerEvents: 'none',
  },
  loadingSpinner: {
    width: 32,
    height: 32,
    borderRadius: '50%',
    border: '1.5px solid rgba(185,120,255,0.12)',
    borderTopColor: 'rgba(185,120,255,0.5)',
    animation: 'spin 1s linear infinite',
  },
  loadingText: {
    fontSize: 11,
    letterSpacing: '0.08em',
    color: 'rgba(226,244,255,0.22)',
  },
  questionHeader: {
    marginBottom: 14,
    paddingBottom: 10,
    borderBottom: '1px solid rgba(226,244,255,0.05)',
  },
  questionLabel: {
    fontSize: 9,
    letterSpacing: '0.16em',
    color: 'rgba(185,120,255,0.4)',
    textTransform: 'lowercase',
    marginBottom: 5,
  },
  questionText: {
    margin: 0,
    fontSize: 13,
    color: 'rgba(226,244,255,0.38)',
    lineHeight: 1.5,
    fontStyle: 'italic',
    fontFamily: "'Crimson Pro', Georgia, serif",
  },
  inputContainer: {
    flexShrink: 0,
    padding: '8px 12px',
    borderTop: '1px solid rgba(226,244,255,0.05)',
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    background: 'rgba(0,0,0,0.06)',
  },
  inputField: {
    flex: 1,
    background: 'transparent',
    border: 'none',
    outline: 'none',
    color: 'rgba(226,244,255,0.85)',
    fontFamily: "'Crimson Pro', Georgia, serif",
    fontSize: 13,
    padding: '4px 2px',
  },
  sendBtn: {
    background: 'none',
    border: 'none',
    fontSize: 10,
    fontWeight: 700,
    letterSpacing: '0.10em',
    padding: '4px 6px',
    whiteSpace: 'nowrap',
    transition: 'color 0.2s ease',
  }
};