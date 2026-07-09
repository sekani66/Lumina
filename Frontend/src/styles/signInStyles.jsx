export const AppleIcon = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M16.365 1.43c0 1.14-.417 2.06-1.25 2.79-.833.73-1.79 1.13-2.87 1.03-.114-1.1.325-2.06 1.17-2.87.85-.82 1.83-1.28 2.95-1.36v.41ZM20.5 17.02c-.35.82-.77 1.6-1.27 2.35-.68 1.01-1.24 1.71-1.68 2.1-.68.63-1.41.96-2.2.98-.56.02-1.24-.16-2.03-.53-.79-.37-1.51-.55-2.17-.55-.68 0-1.42.18-2.22.55-.8.37-1.44.56-1.94.58-.76.03-1.5-.31-2.24-1-.47-.42-1.06-1.16-1.77-2.2-.76-1.12-1.39-2.42-1.87-3.9-.52-1.6-.78-3.16-.78-4.66 0-1.72.37-3.2 1.11-4.44.58-1 1.35-1.78 2.32-2.36.97-.58 2.01-.88 3.12-.9.6-.01 1.38.19 2.36.6.98.41 1.6.62 1.88.62.21 0 .9-.24 2.06-.72 1.1-.44 2.03-.63 2.79-.55 2.06.17 3.61 1 4.64 2.5-1.84 1.12-2.75 2.68-2.74 4.68.02 1.56.58 2.85 1.7 3.88.5.48 1.07.85 1.7 1.11-.14.4-.29.79-.44 1.16Z"/>
    </svg>
)

const blue  = '#63c8ff'
const dark  = '#070b14'
const card  = '#0c1422'
const text1 = '#e2f4ff'
const text2 = 'rgba(226,244,255,0.55)'
const text3 = 'rgba(226,244,255,0.28)'

export const S = {
  root: {
    minHeight: '100vh', width: '100%',
    background: dark,
    display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center',
    position: 'relative', overflow: 'hidden',
    padding: '80px 24px 40px',
    fontFamily: '"Cabinet Grotesk", sans-serif',
    color: text1,
  },

  mesh: {
    position: 'fixed', inset: 0, pointerEvents: 'none',
    background: `
      radial-gradient(ellipse 70% 60% at 15% 20%, rgba(99,200,255,0.08) 0%, transparent 60%),
      radial-gradient(ellipse 55% 45% at 85% 75%, rgba(120,80,255,0.07) 0%, transparent 60%)
    `,
  },
  grid: {
    position: 'fixed', inset: 0, pointerEvents: 'none',
    backgroundImage: `
      linear-gradient(rgba(99,200,255,0.025) 1px, transparent 1px),
      linear-gradient(90deg, rgba(99,200,255,0.025) 1px, transparent 1px)
    `,
    backgroundSize: '52px 52px',
  },
  particleLayer: { position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0 },

  backLink: {
    position: 'fixed', top: 22, left: 24, zIndex: 60,
    background: 'none', border: 'none', cursor: 'pointer',
    color: text3, fontSize: 12,
    fontFamily: '"DM Mono", monospace', letterSpacing: '0.06em',
    display: 'flex', alignItems: 'center', gap: 6,
    transition: 'color 0.2s', padding: '6px 0',
  },

  // ── Split shell ──
  shell: {
    position: 'relative', zIndex: 2,
    display: 'flex', width: '100%', maxWidth: 1000,
    minHeight: 620,
    borderRadius: 22,
    overflow: 'hidden',
    border: '1px solid rgba(99,200,255,0.12)',
    boxShadow: `
      0 0 0 1px rgba(99,200,255,0.05),
      0 32px 90px rgba(0,0,0,0.65),
      0 4px 24px rgba(0,0,0,0.4)
    `,
  },

  // ── Left panel ──
  leftPanel: {
    flex: '0 0 42%',
    background: `linear-gradient(160deg, #0e1a2e 0%, #080f1c 100%)`,
    borderRight: '1px solid rgba(99,200,255,0.1)',
    display: 'flex', alignItems: 'stretch',
    position: 'relative', overflow: 'hidden',
  },
  leftInner: {
    padding: '48px 44px',
    display: 'flex', flexDirection: 'column', gap: 28,
    flex: 1,
  },

  logoRow: { display: 'flex', alignItems: 'center', gap: 10 },
  logoMark: {
    width: 36, height: 36, borderRadius: 10,
    background: 'linear-gradient(135deg, #63c8ff 0%, #3a8eff 100%)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    boxShadow: '0 0 22px rgba(99,200,255,0.3)', flexShrink: 0,
  },
  logoLetter: { color: '#07111f', fontWeight: 900, fontSize: 20 },
  logoWord: { fontSize: 20, fontWeight: 800, color: text1, letterSpacing: '-0.02em' },

  leftHeading: {
    fontSize: 'clamp(26px, 3.5vw, 38px)',
    fontWeight: 900, lineHeight: 1.12,
    letterSpacing: '-0.03em',
    fontFamily: '"Cabinet Grotesk", sans-serif',
  },
  leftEm: {
    fontStyle: 'italic',
    fontFamily: '"Crimson Pro", Georgia, serif',
    fontWeight: 300, fontSize: '1.08em',
  },
  leftAccent: { color: blue },

  leftSub: {
    fontSize: 14, color: text2, lineHeight: 1.7,
    fontFamily: '"Crimson Pro", Georgia, serif',
    fontWeight: 300, maxWidth: 280,
  },

  statsRow: { display: 'flex', gap: 24 },
  statBlock: { display: 'flex', flexDirection: 'column', gap: 3 },
  statNum: { fontSize: 22, fontWeight: 800, color: blue, letterSpacing: '-0.02em' },
  statLabel: { fontSize: 10, color: text3, fontFamily: '"DM Mono", monospace', letterSpacing: '0.12em' },

  // ── Right panel (form) ──
  rightPanel: {
    flex: 1,
    background: 'linear-gradient(160deg, #0c1422 0%, #080e1a 100%)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    padding: '44px 48px',
  },
  formCard: {
    width: '100%', maxWidth: 380,
    display: 'flex', flexDirection: 'column', gap: 22,
  },

  formHead: { display: 'flex', flexDirection: 'column', gap: 6 },
  formH1: {
    fontSize: 26, fontWeight: 900, color: text1,
    letterSpacing: '-0.03em', lineHeight: 1.1,
  },

  socialRow: { display: 'flex', gap: 10 },
  socialIconBtn: {
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    flex: 1, height: 46, borderRadius: 11,
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid rgba(226,244,255,0.09)',
    color: text2, cursor: 'pointer',
    transition: 'border-color 0.18s, background 0.18s, color 0.18s',
  },

  divider: { display: 'flex', alignItems: 'center', gap: 10 },
  divLine:  { flex: 1, height: 1, background: 'rgba(99,200,255,0.09)' },
  divLabel: { fontSize: 10.5, color: text3, fontFamily: '"DM Mono", monospace', letterSpacing: '0.07em', whiteSpace: 'nowrap' },

  form: { display: 'flex', flexDirection: 'column', gap: 16 },

  inputWrap: { position: 'relative', display: 'flex', alignItems: 'center' },
  forgotBtn: {
    background: 'none', border: 'none', cursor: 'pointer',
    fontSize: 11.5, color: text3,
    fontFamily: '"Cabinet Grotesk", sans-serif',
    letterSpacing: '0.02em', transition: 'color 0.18s', padding: 0,
  },

  eyeBtn: {
    position: 'absolute', right: 14, zIndex: 1,
    background: 'none', border: 'none', cursor: 'pointer',
    display: 'flex', alignItems: 'center',
    opacity: 0.7, transition: 'opacity 0.18s', padding: 0,
  },

  submitBtn: {
    width: '100%', padding: '14px',
    borderRadius: 11, border: 'none',
    fontSize: 14.5, fontWeight: 800,
    fontFamily: '"Cabinet Grotesk", sans-serif',
    letterSpacing: '0.02em',
    display: 'flex', alignItems: 'center',
    justifyContent: 'center', gap: 9,
    marginTop: 2,
  },

  nudge: { textAlign: 'center', fontSize: 13, color: text2 },
  nudgeLink: {
    background: 'none', border: 'none', cursor: 'pointer',
    color: blue, fontWeight: 700, fontSize: 13,
    fontFamily: '"Cabinet Grotesk", sans-serif',
    transition: 'color 0.18s',
  },

  footNote: {
    position: 'relative', zIndex: 2,
    marginTop: 28, fontSize: 10.5,
    color: 'rgba(226,244,255,0.14)',
    fontFamily: '"DM Mono", monospace', letterSpacing: '0.1em',
  },
}