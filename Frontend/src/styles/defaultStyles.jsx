
const blue   = '#63c8ff'
const blueLo = 'rgba(99,200,255,0.12)'
const dark   = '#070b14'
const card   = '#0c1220'
const text1  = '#e2f4ff'
const text2  = 'rgba(226,244,255,0.55)'
const text3  = 'rgba(226,244,255,0.28)'

export const Styles = {
    root: {
        minHeight: '100vh',
        width: '100%',
        background: dark,
        color: text1,
        fontFamily: '"Cabinet Grotesk", "DM Sans", sans-serif',
        overflowX: 'hidden',
        position: 'relative',
    },

    // Background layers
    particleLayer: { position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0 },
    mesh: {
        position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0,
        background: `
            radial-gradient(ellipse 80% 60% at 20% 10%, rgba(99,200,255,0.07) 0%, transparent 60%),
            radial-gradient(ellipse 60% 50% at 80% 80%, rgba(120,80,255,0.06) 0%, transparent 60%),
            radial-gradient(ellipse 40% 40% at 60% 30%, rgba(99,200,255,0.04) 0%, transparent 50%)
        `,
    },
    gridLines: {
        position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0,
        backgroundImage: `
            linear-gradient(rgba(99,200,255,0.025) 1px, transparent 1px),
            linear-gradient(90deg, rgba(99,200,255,0.025) 1px, transparent 1px)
        `,
        backgroundSize: '52px 52px',
    },

    // NAVIGATION
    nav: {
        position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
        display: 'flex', alignItems: 'center', gap: 0,
        padding: '0 40px', height: 64,
        transition: 'background 0.3s, box-shadow 0.3s, border-color 0.3s',
    },
    logo: { display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none', marginRight: 'auto' },
    logoMark: {
        width: 34, height: 34, borderRadius: 9,
        background: `linear-gradient(135deg, ${blue} 0%, #3a8eff 100%)`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        boxShadow: `0 0 20px rgba(99,200,255,0.35)`,
        flexShrink: 0,
    },
    logoMarkInner: { color: '#07111f', fontWeight: 900, fontSize: 18, fontFamily: '"Cabinet Grotesk", sans-serif' },
    logoText: { fontSize: 20, fontWeight: 800, color: text1, letterSpacing: '-0.02em', fontFamily: '"Cabinet Grotesk", sans-serif' },
    logoBadge: {
        fontSize: 9, fontFamily: '"DM Mono", monospace', letterSpacing: '0.15em',
        padding: '2px 6px', borderRadius: 4,
        background: blueLo, border: `1px solid rgba(99,200,255,0.25)`,
        color: blue,
    },
    navLinks: { display: 'flex', gap: 32, margin: '0 40px' },
    navLink: {
        fontSize: 14, color: text2, textDecoration: 'none',
        fontWeight: 500, letterSpacing: '0.01em', transition: 'color 0.15s',
        cursor: 'pointer',
    },
    navAuth: { display: 'flex', gap: 10, alignItems: 'center' },
    navSignIn: {
        background: 'transparent', border: `1px solid rgba(99,200,255,0.22)`,
        color: text2, borderRadius: 8, padding: '8px 18px',
        fontSize: 14, fontWeight: 500, cursor: 'pointer',
        fontFamily: '"Cabinet Grotesk", sans-serif',
        transition: 'all 0.2s',
    },
    navSignUp: {
        background: `linear-gradient(135deg, ${blue} 0%, #3a8eff 100%)`,
        border: 'none', borderRadius: 8, padding: '8px 20px',
        fontSize: 14, fontWeight: 700, color: '#07111f',
        cursor: 'pointer', fontFamily: '"Cabinet Grotesk", sans-serif',
        display: 'flex', alignItems: 'center', gap: 6,
    },
    hamburger: {
        display: 'none', flexDirection: 'column', gap: 5,
        background: 'none', border: 'none', cursor: 'pointer', padding: 8,
    },
    hamBar: { display: 'block', width: 22, height: 2, background: text2, borderRadius: 2, transition: 'opacity 0.2s' },
    mobileMenu: {
        position: 'fixed', top: 64, left: 0, right: 0, zIndex: 99,
        background: 'rgba(7,11,20,0.97)', backdropFilter: 'blur(20px)',
        borderBottom: '1px solid rgba(99,200,255,0.1)',
        display: 'flex', flexDirection: 'column', gap: 6, padding: '16px 24px 24px',
    },
    mobileLink: { color: text2, textDecoration: 'none', padding: '10px 0', fontSize: 16, fontWeight: 500 },

    // HERO
    hero: {
        position: 'relative', zIndex: 2,
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        textAlign: 'center',
        padding: '160px 24px 80px',
        maxWidth: 900, margin: '0 auto',
    },
    heroBadge: {
        display: 'inline-flex', alignItems: 'center', gap: 8,
        padding: '6px 16px', borderRadius: 20,
        background: blueLo, border: `1px solid rgba(99,200,255,0.25)`,
        fontSize: 12, fontFamily: '"DM Mono", monospace', letterSpacing: '0.08em',
        color: blue, marginBottom: 32, position: 'relative',
    },
    badgePulse: {
        display: 'inline-block', width: 6, height: 6, borderRadius: '50%',
        background: blue, boxShadow: `0 0 8px ${blue}`,
        animation: 'pulseRing 1.5s ease-out infinite',
    },
    heroH1: {
        fontSize: 'clamp(48px, 7vw, 80px)',
        fontWeight: 900, lineHeight: 1.06, letterSpacing: '-0.03em',
        color: text1, marginBottom: 28,
        fontFamily: '"Cabinet Grotesk", sans-serif',
        animation: 'fadeSlideUp 0.7s ease 0.1s both',
    },
    heroEm: {
        fontStyle: 'italic', fontFamily: '"Crimson Pro", Georgia, serif',
        fontWeight: 300, fontSize: '1.1em', letterSpacing: '-0.01em',
    },
    heroAccent: { color: blue },
    heroSub: {
        fontSize: 18, lineHeight: 1.75, color: text2, maxWidth: 560,
        marginBottom: 40, fontFamily: '"Crimson Pro", Georgia, serif', fontWeight: 300,
        animation: 'fadeSlideUp 0.7s ease 0.25s both',
    },
    heroCtas: {
        display: 'flex', gap: 14, flexWrap: 'wrap', justifyContent: 'center', marginBottom: 32,
        animation: 'fadeSlideUp 0.7s ease 0.4s both',
    },
    ctaPrimary: {
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '16px 40px', borderRadius: 12,
        background: `linear-gradient(135deg, ${blue} 0%, #3a8eff 100%)`,
        color: '#07111f', border: 'none', cursor: 'pointer',
        fontSize: 16, fontWeight: 800, fontFamily: '"Cabinet Grotesk", sans-serif',
        letterSpacing: '0.01em',
    },
    ctaSecondary: {
        display: 'flex', alignItems: 'center', gap: 10,
        padding: '16px 32px', borderRadius: 12,
        background: 'transparent', border: `1px solid rgba(99,200,255,0.25)`,
        color: text2, cursor: 'pointer',
        fontSize: 16, fontWeight: 600, fontFamily: '"Cabinet Grotesk", sans-serif',
    },
    socialProof: {
        display: 'flex', alignItems: 'center', gap: 12,
        marginBottom: 56, animation: 'fadeSlideUp 0.7s ease 0.55s both',
    },
    proofAvatars: { display: 'flex' },
    proofAvatar: { width: 28, height: 28, borderRadius: '50%', border: `2px solid ${dark}` },
    proofText: { fontSize: 13, color: text3, fontFamily: '"DM Mono", monospace' },

    // Board preview
    boardPreview: {
        position: 'relative', width: '100%', maxWidth: 780,
        borderRadius: 16,
        border: `1px solid rgba(99,200,255,0.2)`,
        background: '#080e1a',
        boxShadow: `0 0 0 1px rgba(99,200,255,0.08), 0 40px 120px rgba(0,0,0,0.7), 0 0 80px rgba(99,200,255,0.06)`,
        overflow: 'hidden',
        animation: 'fadeSlideUp 0.8s ease 0.6s both',
        marginTop: 60,
    },
    scanLine: {
        position: 'absolute', left: 0, right: 0, height: 2,
        background: `linear-gradient(90deg, transparent, rgba(99,200,255,0.25), transparent)`,
        animation: 'scanLine 4s linear infinite',
        pointerEvents: 'none', zIndex: 5,
    },
    cornerDot: {
        position: 'absolute', width: 6, height: 6, borderRadius: '50%',
        background: blue, opacity: 0.6,
    },
    boardInner: { position: 'relative', zIndex: 2 },
    boardHeader: {
        display: 'flex', alignItems: 'center', gap: 10,
        padding: '12px 18px',
        borderBottom: '1px solid rgba(99,200,255,0.1)',
        background: 'rgba(99,200,255,0.04)',
    },
    boardDots: { display: 'flex', gap: 6 },
    boardDot: { width: 11, height: 11, borderRadius: '50%' },
    boardTitle: { flex: 1, fontSize: 11, fontFamily: '"DM Mono", monospace', color: text3, letterSpacing: '0.12em' },
    boardLive: { fontSize: 9, fontFamily: '"DM Mono", monospace', color: '#4dff91', letterSpacing: '0.18em', animation: 'pulseRing 2s ease-out infinite' },
    boardScreen: {
        padding: '28px 36px 32px',
        display: 'flex', flexDirection: 'column', gap: 6, minHeight: 240,
    },
    previewLine: { lineHeight: 1.5 },
    cursor: {
        width: 2, height: 18,
        background: blue,
        marginTop: 8,
        animation: 'pulseRing 1s ease-in-out infinite',
        borderRadius: 1,
    },

    // HOW IT WORKS
    howSection: {
        position: 'relative', zIndex: 2,
        padding: '100px 40px',
        textAlign: 'center',
        background: 'rgba(99,200,255,0.025)',
        borderTop: '1px solid rgba(99,200,255,0.07)',
        borderBottom: '1px solid rgba(99,200,255,0.07)',
    },
    stepsRow: {
        display: 'flex', alignItems: 'flex-start', justifyContent: 'center',
        gap: 0, flexWrap: 'wrap', maxWidth: 900, margin: '60px auto 0',
    },
    stepNode: {
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        flex: '1 1 180px', position: 'relative', cursor: 'default',
    },
    stepNumWrap: { position: 'relative', marginBottom: 16 },
    stepRing: {
        position: 'absolute', inset: -6,
        borderRadius: '50%', border: `1px solid ${blue}`,
        opacity: 0,
    },
    stepNum: {
        width: 52, height: 52, borderRadius: '50%',
        background: blueLo, border: `1px solid rgba(99,200,255,0.3)`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 13, fontFamily: '"DM Mono", monospace', color: blue, fontWeight: 500,
    },
    stepConnector: {
        position: 'absolute', top: 26, left: 'calc(50% + 26px)',
        right: 'calc(-50% + 26px)', height: 1,
        background: 'linear-gradient(90deg, rgba(99,200,255,0.3), rgba(99,200,255,0.05))',
    },
    stepLabel: {
        fontSize: 14, color: text2, maxWidth: 140,
        textAlign: 'center', lineHeight: 1.5, fontWeight: 500,
    },

    // FEATURES
    featuresSection: {
        position: 'relative', zIndex: 2,
        padding: '100px 40px',
        maxWidth: 1200, margin: '0 auto',
        textAlign: 'center',
    },
    featuresGrid: {
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
        gap: 20, marginTop: 60, textAlign: 'left',
    },
    featureCard: {
        background: card,
        border: '1px solid rgba(99,200,255,0.1)',
        borderRadius: 14, padding: '28px 28px 32px',
        cursor: 'default',
        boxShadow: '0 4px 24px rgba(0,0,0,0.3)',
        transition: 'border-color 0.2s, box-shadow 0.2s, transform 0.2s',
    },
    featureIcon: {
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: 44,
        height: 44,
        borderRadius: 12,
        background: 'linear-gradient(135deg, rgba(99,200,255,0.1) 0%, rgba(99,200,255,0.02) 100%)',
        border: '1px solid rgba(99,200,255,0.15)',
        color: '#63c8ff',
        marginBottom: 20,
    },
    featureTitle: { fontSize: 16, fontWeight: 700, color: text1, marginBottom: 10, letterSpacing: '-0.01em' },
    featureBody: { fontSize: 15, color: text2, lineHeight: 1.7, fontFamily: '"Crimson Pro", Georgia, serif', fontWeight: 300 },

    // CLARITY (not / is)
    claritySection: {
        position: 'relative', zIndex: 2,
        padding: '80px 40px',
        background: 'rgba(99,200,255,0.02)',
        borderTop: '1px solid rgba(99,200,255,0.07)',
        borderBottom: '1px solid rgba(99,200,255,0.07)',
    },
    clarityGrid: {
        display: 'flex', gap: 0, maxWidth: 900, margin: '0 auto',
        flexWrap: 'wrap',
    },
    clarityCol: { flex: '1 1 300px', padding: '0 40px', display: 'flex', flexDirection: 'column', gap: 16 },
    claritySep: { width: 1, background: 'rgba(99,200,255,0.12)', margin: '0 20px', minHeight: 200, flexShrink: 0 },
    clarityLabel: {
        fontSize: 10, letterSpacing: '0.22em', fontFamily: '"DM Mono", monospace',
        textTransform: 'uppercase', color: 'rgba(255,107,107,0.7)',
        marginBottom: 8,
    },
    clarityRow: { display: 'flex', alignItems: 'flex-start' },
    clarityText: { fontSize: 15, color: text2, lineHeight: 1.5, fontFamily: '"Crimson Pro", Georgia, serif' },

    // SUBJECTS
    subjectsSection: {
        position: 'relative', zIndex: 2,
        padding: '100px 40px',
        textAlign: 'center',
        maxWidth: 900, margin: '0 auto',
    },
    subjectsRow: {
        display: 'flex', flexWrap: 'wrap', gap: 14,
        justifyContent: 'center', marginTop: 48,
    },
    subjectPill: {
        padding: '14px 32px', borderRadius: 40,
        border: `1px solid rgba(99,200,255,0.25)`,
        background: blueLo, color: text1,
        fontSize: 15, fontWeight: 600, letterSpacing: '0.02em',
    },

    // CTA BANNER
    ctaBanner: {
        position: 'relative', zIndex: 2,
        padding: '120px 40px',
        textAlign: 'center',
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 24,
        overflow: 'hidden',
    },
    ctaBannerGlow: {
        position: 'absolute', top: '20%', left: '50%',
        transform: 'translateX(-50%)',
        width: 600, height: 300,
        background: 'radial-gradient(ellipse, rgba(99,200,255,0.1) 0%, transparent 70%)',
        pointerEvents: 'none',
    },   
    ctaBannerEye: {
        fontSize: 11, letterSpacing: '0.25em', fontFamily: '"DM Mono", monospace',
        color: blue, textTransform: 'uppercase',
    },
    ctaBannerH: {
        fontSize: 'clamp(32px, 5vw, 52px)',
        fontWeight: 900, letterSpacing: '-0.03em', lineHeight: 1.1,
        fontFamily: '"Cabinet Grotesk", sans-serif',
    },

    // FOOTER
    footer: {
        position: 'relative', zIndex: 2,
        borderTop: '1px solid rgba(99,200,255,0.08)',
        padding: '48px 40px',
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16,
        textAlign: 'center',
    },
    footerLogo: { display: 'flex', alignItems: 'center', gap: 10 },
    footerSub: { fontSize: 13, color: text3, maxWidth: 400, lineHeight: 1.6 },
    footerLinks: { display: 'flex', gap: 28, flexWrap: 'wrap', justifyContent: 'center' },
    footerLink: { fontSize: 13, color: text3, textDecoration: 'none', transition: 'color 0.15s' },
    footerCopy: { fontSize: 11, color: 'rgba(226,244,255,0.15)', fontFamily: '"DM Mono", monospace' },

    // Shared section typography
    sectionEyebrow: {
        fontSize: 15, letterSpacing: '0.25em', fontFamily: '"DM Mono", monospace',
        color: blue, textTransform: 'uppercase', marginBottom: 14,
    },
    sectionH2: {
        fontSize: 'clamp(28px, 4vw, 44px)',
        fontWeight: 900, letterSpacing: '-0.03em',
        fontFamily: '"Cabinet Grotesk", sans-serif',
        color: text1,
    },
}