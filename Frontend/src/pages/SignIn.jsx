import React, { useState, useEffect } from 'react';

import '../styles/authStyles.css';

import { Field, IconSlot, Spinner } from '../utils/signinHelper';
import { MailIcon,GoogleIcon, MicrosoftIcon, LockIcon, EyeIcon, EyeOffIcon, ArrowLeft } from '../styles/icons';

const PARTICLES = [
    { char: '∫', x: '7%',  y: '12%', size: 80, delay: '0s',   dur: '7s'  },
    { char: 'Σ', x: '91%', y: '18%', size: 60, delay: '1.4s', dur: '9s'  },
    { char: 'π', x: '5%',  y: '68%', size: 70, delay: '0.7s', dur: '8s'  },
    { char: '∇', x: '88%', y: '72%', size: 54, delay: '2.1s', dur: '10s' },
    { char: '∞', x: '93%', y: '44%', size: 50, delay: '1.9s', dur: '6s'  },
    { char: 'Δ', x: '3%',  y: '50%', size: 58, delay: '1.0s', dur: '11s' },
    { char: 'λ', x: '95%', y: '28%', size: 46, delay: '1.6s', dur: '8s'  },
    { char: '∂', x: '48%', y: '88%', size: 52, delay: '2.6s', dur: '9s'  },
    { char: 'ℏ', x: '22%', y: '5%',  size: 44, delay: '3.0s', dur: '7s'  },
    { char: 'θ', x: '72%', y: '92%', size: 48, delay: '0.3s', dur: '10s' },
]
export default function SignInPage({ onNavigate }) {
    const [form,      setForm]      = useState({ email: '', password: '' })
    const [showPass,  setShowPass]  = useState(false)
    const [remember,  setRemember]  = useState(false)
    const [focused,   setFocused]   = useState(null)
    const [mounted,   setMounted]   = useState(false)
    const [loading,   setLoading]   = useState(false)

    useEffect(() => { const t = setTimeout(() => setMounted(true), 40); return () => clearTimeout(t) }, [])

    const set = f => e => setForm(p => ({ ...p, [f]: e.target.value }))

    const handleSubmit = async e => {
        e.preventDefault()
        setLoading(true)
        await new Promise(r => setTimeout(r, 820))   // brief auth feel
        onNavigate('lesson')
    }

    return (
        <div style={S.root}>

            {/* Background layers */}
            <div style={S.mesh}   aria-hidden />
            <div style={S.grid}   aria-hidden />

            {/* Particles */}
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
            {/* Back link */}
            <button className="si-back" onClick={() => onNavigate('default')} style={S.backLink}>
                <ArrowLeft /> Back to Lumina
            </button>

        {/* Split layout  */}
        <div style={{
            ...S.shell,
            opacity:   mounted ? 1 : 0,
            transform: mounted ? 'translateY(0)' : 'translateY(30px)',
            transition: 'opacity 0.5s ease, transform 0.5s ease',
        }}>
        {/* Left panel branding  */}
        <div style={S.leftPanel}>
            <div style={S.leftInner}>
                {/* Logo */}
                <div style={S.logoRow}>
                <div style={S.logoMark}>
                <span style={S.logoLetter}>L</span>
            </div>
            <span style={S.logoWord}>Lumina</span>
        </div>

        {/* Tagline */}
            <h2 style={S.leftHeading}>
                Every lesson<br/>
                <em style={S.leftEm}>shaped</em> for<br />
                <span style={S.leftAccent}>you alone.</span>
            </h2>
            <p style={S.leftSub}>
                Sign in to resume your personalised learning journey —
                right where your AI teacher left off.
            </p>

            {/* Decorative board preview strip */}
            <div style={S.boardStrip}>
                {STRIP_LINES.map((line, i) => (
                    <div key={i} style={{
                        ...S.stripLine,
                        animationDelay: `${i * 1.1}s`,
                        opacity: 0,
                        animation: `fadeUp 0.45s ease ${i * 1.1 + 0.4}s forwards`,
                        color:      line.accent ? '#63c8ff' : 'rgba(226,244,255,0.55)',
                        fontSize:   line.big    ? 18 : 12,
                        fontFamily: line.big    ? '"Crimson Pro", serif' : '"DM Mono", monospace',
                        letterSpacing: line.big ? 0 : '0.06em',
                        borderLeft: line.big ? '2px solid rgba(99,200,255,0.35)' : 'none',
                        paddingLeft: line.big ? 10 : 0,
                    }}>{line.text}</div>
                ))}
                <div style={S.stripCursor} />
                </div>
            </div>
        </div>

        {/* Right panel — form */}
        <div style={S.rightPanel}>
            <div style={S.formCard}>
                {/* Header */}
                <div style={S.formHead}>
                    <h1 style={S.formH1}>Welcome back</h1>
                    <p style={S.formSub}>Sign in to continue your lesson</p>
                </div>
            {/* Social login */}
            <div style={S.socialCol}>
                {[
                    { Icon: GoogleIcon,    label: 'Continue with Google'    },
                    { Icon: MicrosoftIcon, label: 'Continue with Microsoft' },
                ].map(({ Icon, label }) => (
                    <button key={label} className="si-social" style={S.socialBtn}
                        onClick={() => onNavigate('lesson')}>
                            <Icon />
                            <span>{label}</span>
                    </button>
                ))}
            </div>

            {/* Divider */}
            <div style={S.divider}>
                <div style={S.divLine} />
                <span style={S.divLabel}>or continue with email</span>
                <div style={S.divLine} />
            </div>

            {/* Form fields  */}
            <form onSubmit={handleSubmit} style={S.form} noValidate>
                {/* Email */}
                <Field label="Email address">
                    <div style={S.inputWrap}>
                        <IconSlot><MailIcon active={focused === 'email'} /></IconSlot>
                        <input
                            className="si-input"
                            type="email"
                            placeholder="you@university.edu"
                            value={form.email}
                            onChange={set('email')}
                            onFocus={() => setFocused('email')}
                            onBlur={() => setFocused(null)}
                            autoComplete="email"
                        />
                    </div>
                </Field>
                {/* Password */}
                <Field label="Password" right={
                    <button type="button" className="si-forgot" style={S.forgotBtn}>
                        Forgot password?
                    </button>}>
                    <div style={S.inputWrap}>
                        <IconSlot><LockIcon active={focused === 'password'} /></IconSlot>
                        <input
                            className="si-input"
                            type={showPass ? 'text' : 'password'}
                            placeholder="Enter your password"
                            value={form.password}
                            onChange={set('password')}
                            onFocus={() => setFocused('password')}
                            onBlur={() => setFocused(null)}
                            autoComplete="current-password"
                            style={{ paddingRight: 46 }}
                        />
                        <button
                            type="button"
                            className="si-eyebtn"
                            onClick={() => setShowPass(v => !v)}
                            style={S.eyeBtn}
                            aria-label={showPass ? 'Hide password' : 'Show password'}>
                            {showPass ? <EyeOffIcon /> : <EyeIcon />}
                        </button>
                    </div>
                </Field>

                {/* Remember me */}
                <div style={S.rememberRow}>
                    <button
                        type="button"
                        onClick={() => setRemember(v => !v)}
                        style={{
                            ...S.checkbox,
                            background:  remember ? '#63c8ff' : 'transparent',
                            borderColor: remember ? '#63c8ff' : 'rgba(99,200,255,0.22)',
                        }}
                        role="checkbox"
                        aria-checked={remember}>
                        {remember && <CheckIcon />}
                    </button>
                    <span style={S.rememberText}>Keep me signed in for 30 days</span>
                </div>

               {/* Submit */}
                <button
                    type="submit"
                    className="si-submit"
                    disabled={loading}
                    style={{
                        ...S.submitBtn,
                        background: loading
                        ? 'rgba(99,200,255,0.28)'
                        : 'linear-gradient(135deg, #63c8ff 0%, #3a8eff 100%)',
                        color:  loading ? 'rgba(7,17,31,0.55)' : '#07111f',
                        cursor: loading ? 'not-allowed' : 'pointer',
                        animation: loading ? 'none' : 'glowPulse 3s ease-in-out infinite',
                        transition: 'transform 0.18s ease, box-shadow 0.18s ease, background 0.3s',
                        
                    }}onClick={() => onNavigate('home')}
                    >
                    {
                        loading? <><Spinner /> Signing in…</> 
                        : <>Sign in to Lumina <span style={{ fontSize: 18 }}>→</span></>
                    }
                </button>
            </form>
                {/* Sign up nudge  NOW routes to 'signup' */}
                <p style={S.nudge}> New to Lumina?{' '}
                    <button
                        className="si-newlink"
                        style={S.nudgeLink}
                        onClick={() => onNavigate('signup')}>
                        Create a free account
                    </button>
                </p>
                {/* Legal */}
                <p style={S.legal}>
                    By signing in you agree to our{' '}
                    <a href="#" style={S.legalLink}>Terms</a> and{' '}
                    <a href="#" style={S.legalLink}>Privacy Policy</a>.
                </p>
            </div>
        </div>
    </div>
    {/* Footer note */}
    <p style={S.footNote}>Lumina · Real-time AI teaching for serious learners</p>
    </div>
    )
}

// ─── Board strip preview data ──────────────────────────────────────────────────
const STRIP_LINES = [
  { text: 'LESSON · Quadratic Equations', accent: false },
  { text: '2x² + 6x + 4 = 0',            big: true     },
  { text: 'STEP 01 — divide by 2',        accent: false },
  { text: 'x² + 3x + 2 = 0',             big: true, accent: true },
  { text: 'STEP 02 — factor',             accent: false },
  { text: '(x + 1)(x + 2) = 0',          big: true     },
]

// ─── Styles ───────────────────────────────────────────────────────────────────
const blue  = '#63c8ff'
const dark  = '#070b14'
const card  = '#0c1422'
const text1 = '#e2f4ff'
const text2 = 'rgba(226,244,255,0.55)'
const text3 = 'rgba(226,244,255,0.28)'

const S = {
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

  // Board preview strip inside left panel
  boardStrip: {
    background: 'rgba(7,11,20,0.55)',
    border: '1px solid rgba(99,200,255,0.1)',
    borderRadius: 12,
    padding: '18px 20px 20px',
    display: 'flex', flexDirection: 'column', gap: 6,
    marginTop: 'auto',
    overflow: 'hidden',
    position: 'relative',
  },
  stripLine: { lineHeight: 1.5 },
  stripCursor: {
    width: 2, height: 16, background: blue,
    borderRadius: 1, marginTop: 4,
    animation: 'blink 1.1s ease-in-out infinite',
  },

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
  formSub: {
    fontSize: 14, color: text2,
    fontFamily: '"Crimson Pro", Georgia, serif',
    fontWeight: 300,
  },

  socialCol: { display: 'flex', flexDirection: 'column', gap: 9 },
  socialBtn: {
    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 11,
    width: '100%', padding: '11px 16px', borderRadius: 10,
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid rgba(226,244,255,0.09)',
    color: text2, fontSize: 13.5, fontWeight: 600,
    cursor: 'pointer', fontFamily: '"Cabinet Grotesk", sans-serif',
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

  rememberRow: { display: 'flex', alignItems: 'center', gap: 9, marginTop: -2 },
  checkbox: {
    width: 17, height: 17, borderRadius: 5,
    border: '1.5px solid rgba(99,200,255,0.22)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    cursor: 'pointer', flexShrink: 0, padding: 0,
    transition: 'background 0.18s, border-color 0.18s',
    background: 'transparent',
  },
  rememberText: { fontSize: 12.5, color: text2 },

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

  legal: { textAlign: 'center', fontSize: 10.5, color: text3, fontFamily: '"DM Mono", monospace', lineHeight: 1.6 },
  legalLink: { color: text3, textDecoration: 'underline', textUnderlineOffset: 3 },

  footNote: {
    position: 'relative', zIndex: 2,
    marginTop: 28, fontSize: 10.5,
    color: 'rgba(226,244,255,0.14)',
    fontFamily: '"DM Mono", monospace', letterSpacing: '0.1em',
  },
}