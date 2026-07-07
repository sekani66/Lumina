export const S = {
  root: {
    minHeight: '100vh', width: '100%',
    background: '#050914', color: '#e2f4ff',
    display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center',
    position: 'relative', overflow: 'hidden',
    padding: '80px 24px 40px',
    fontFamily: '"Cabinet Grotesk", sans-serif',
  },
  mesh: {
    position: 'fixed', inset: 0, pointerEvents: 'none',
    background: `
      radial-gradient(ellipse 70% 60% at 85% 20%, rgba(99,200,255,0.06) 0%, transparent 60%),
      radial-gradient(ellipse 55% 45% at 15% 78%, rgba(120,80,255,0.05) 0%, transparent 60%)
    `,
  },
  grid: {
    position: 'fixed', inset: 0, pointerEvents: 'none',
    backgroundImage: `
      linear-gradient(rgba(255,255,255,0.015) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,0.015) 1px, transparent 1px)
    `,
    backgroundSize: '52px 52px',
  },
  particleLayer: { position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0 },

  backLink: {
    position: 'fixed', top: 24, left: 32, zIndex: 60,
    background: 'none', border: 'none', cursor: 'pointer',
    color: 'rgba(226,244,255,0.4)', fontSize: 13,
    fontFamily: '"DM Mono", monospace', letterSpacing: '0.05em',
    display: 'flex', alignItems: 'center', gap: 8,
    transition: 'color 0.2s', padding: '8px 0',
  },

  card: {
    position: 'relative', zIndex: 2, width: '100%',
    background: 'rgba(12, 20, 34, 0.65)',
    backdropFilter: 'blur(20px)',
    borderRadius: 24,
    border: '1px solid rgba(255,255,255,0.08)',
    boxShadow: '0 0 0 1px rgba(99,200,255,0.05), 0 32px 80px rgba(0,0,0,0.8)',
    padding: '48px',
    display: 'flex', flexDirection: 'column', gap: 28,
  },

  stepBar:      { display: 'flex', flexDirection: 'column', gap: 10 },
  stepTrack:    { height: 4, borderRadius: 2, background: 'rgba(255,255,255,0.05)', overflow: 'hidden' },
  stepFill:     { height: '100%', borderRadius: 2, background: 'linear-gradient(90deg, #63c8ff, #a78bfa)' },
  stepLabels:   { display: 'flex', gap: 10, alignItems: 'center', fontSize: 11, fontFamily: '"DM Mono", monospace', letterSpacing: '0.08em', fontWeight: 600 },
  stepLabelText:{ transition: 'color 0.3s' },

  formHead: { display: 'flex', flexDirection: 'column', gap: 8 },
  formH1:   { fontSize: 32, fontWeight: 900, color: '#ffffff', letterSpacing: '-0.02em', lineHeight: 1.2 },
  formSub:  { fontSize: 16, color: 'rgba(226,244,255,0.6)', fontFamily: '"Crimson Pro", Georgia, serif', fontWeight: 300, lineHeight: 1.5 },

  form:  { display: 'flex', flexDirection: 'column', gap: 26 },
  field: { display: 'flex', flexDirection: 'column', gap: 10 },
  label: { fontSize: 13, fontWeight: 700, color: 'rgba(226,244,255,0.7)', letterSpacing: '0.05em', textTransform: 'uppercase' },

  metaHint: {
    fontSize: 12, fontFamily: '"DM Mono", monospace',
    color: 'rgba(226,244,255,0.45)', marginTop: 4,
  },

  fieldError: {
    display: 'flex', alignItems: 'center', gap: 6,
    fontSize: 13, color: '#fb7185', marginTop: 2,
  },

  fileIconWrap: {
    width: 44, height: 44, borderRadius: 10,
    background: 'rgba(99,200,255,0.12)',
    border: '1px solid rgba(99,200,255,0.2)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
  clearFileBtn: {
    marginTop: 4, background: 'none',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: 6, color: 'rgba(226,244,255,0.5)',
    fontSize: 11, fontFamily: '"DM Mono", monospace',
    cursor: 'pointer', padding: '4px 10px',
    transition: 'border-color 0.2s, color 0.2s',
  },

  checkboxRow: { display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer', marginTop: 4 },
  customCheck: {
    width: 20, height: 20, borderRadius: 6, border: '1px solid',
    display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.2s ease',
  },

  reqRow:     { display: 'flex', flexDirection: 'column', gap: 12, padding: '18px', background: 'rgba(255,255,255,0.02)', borderRadius: 16, border: '1px solid rgba(255,255,255,0.05)' },
  reqLabel:   { fontSize: 15, fontWeight: 800, color: '#ffffff' },
  ratingGrid: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 },
  ratingBtn:  { padding: '10px 6px', borderRadius: 10, border: '1px solid', fontSize: 12, fontWeight: 700, cursor: 'pointer', fontFamily: '"Cabinet Grotesk", sans-serif', transition: 'all 0.2s ease' },

  summaryGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 },
  summaryBox:  { background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: 16, padding: '20px', display: 'flex', flexDirection: 'column', gap: 8 },
  summaryTitle:{ fontSize: 12, fontFamily: '"DM Mono", monospace', color: '#63c8ff', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 4, fontWeight: 600 },
  summaryItem: { fontSize: 14, color: 'rgba(226,244,255,0.6)', display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: 6 },

  curriculumBox:        { background: 'linear-gradient(145deg, rgba(99,200,255,0.05), rgba(0,0,0,0))', border: '1px solid rgba(99,200,255,0.15)', borderRadius: 16, padding: '24px' },
  curriculumList:       { display: 'flex', flexDirection: 'column', gap: 12, marginTop: 12 },
  curriculumWrapper:    { background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: 12, overflow: 'hidden', display: 'flex', flexDirection: 'column' },
  curriculumItemHeader: { display: 'flex', alignItems: 'center', gap: 16, padding: '14px 16px', cursor: 'pointer', userSelect: 'none', transition: 'background 0.2s' },
  curriculumIcon:       { width: 32, height: 32, borderRadius: '50%', background: 'rgba(99,200,255,0.15)', color: '#63c8ff', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  curriculumDetails:    { display: 'flex', flexDirection: 'column', gap: 4, flex: 1 },
  curriculumTitle:      { fontSize: 15, fontWeight: 800, color: '#ffffff' },
  curriculumMeta:       { display: 'flex', gap: 8, alignItems: 'center', fontSize: 12, color: 'rgba(226,244,255,0.5)', fontFamily: '"DM Mono", monospace' },
  curriculumBadge:      { padding: '2px 8px', borderRadius: 4, fontSize: 10, fontWeight: 700 },

  lessonsDropdown: { padding: '4px 16px 16px 64px', display: 'flex', flexDirection: 'column', gap: 10, background: 'rgba(0,0,0,0.15)', borderTop: '1px solid rgba(255,255,255,0.02)' },
  lessonRow:       { display: 'flex', alignItems: 'center', gap: 10 },
  lessonBullet:    { width: 5, height: 5, borderRadius: '50%', background: '#63c8ff', opacity: 0.7, flexShrink: 0 },
  lessonText:      { fontSize: 13.5, color: 'rgba(226,244,255,0.8)', fontFamily: '"Cabinet Grotesk", sans-serif' },

  errorBox: { display: 'flex', alignItems: 'center', gap: 12, background: 'rgba(251,113,133,0.08)', border: '1px solid rgba(251,113,133,0.25)', borderRadius: 12, padding: '14px 16px', color: '#fb7185', fontSize: 14 },
  retryBtn: { marginLeft: 'auto', background: 'rgba(251,113,133,0.15)', border: '1px solid rgba(251,113,133,0.3)', borderRadius: 8, color: '#fb7185', fontSize: 12, fontWeight: 700, fontFamily: '"Cabinet Grotesk", sans-serif', cursor: 'pointer', padding: '6px 14px' },

  submitBtn: {
    width: '100%', padding: '16px', borderRadius: 14, border: 'none',
    fontSize: 15, fontWeight: 800, fontFamily: '"Cabinet Grotesk", sans-serif',
    letterSpacing: '0.03em', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
    background: 'linear-gradient(135deg, #63c8ff 0%, #3a8eff 100%)', color: '#050914',
    cursor: 'pointer', animation: 'glowPulse 3s ease-in-out infinite',
    transition: 'transform 0.2s ease, opacity 0.2s ease',
  },
  backStepBtn: {
    background: 'none', border: 'none', cursor: 'pointer',
    color: 'rgba(226,244,255,0.4)', fontSize: 13, fontFamily: '"DM Mono", monospace',
    letterSpacing: '0.04em', textAlign: 'center', transition: 'color 0.2s', padding: '4px 0',
  },
}
export const PARTICLES = [
    { char: '∇', x: '8%',  y: '10%', size: 76, delay: '0s',   dur: '9s'  },
    { char: 'θ', x: '88%', y: '15%', size: 56, delay: '1.1s', dur: '7s'  },
    { char: 'Δ', x: '92%', y: '58%', size: 64, delay: '0.6s', dur: '10s' },
    { char: '∫', x: '4%',  y: '65%', size: 50, delay: '2.0s', dur: '8s'  },
    { char: 'ℏ', x: '50%', y: '90%', size: 44, delay: '1.7s', dur: '9s'  },
    { char: 'π', x: '76%', y: '82%', size: 42, delay: '0.9s', dur: '7s'  },
  ]