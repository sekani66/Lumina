import React, { useState, useEffect } from 'react';

import '../styles/authStyles.css';
import { S, AppleIcon } from '../styles/signInStyles';

import { Field, IconSlot, Spinner } from '../utils/signinHelper';
import { 
    MailIcon,
    GoogleIcon, 
    MicrosoftIcon, 
    LockIcon, 
    EyeIcon, 
    EyeOffIcon, 
    ArrowLeft 
} from '../styles/icons';
import { PARTICLES } from '../constants/floatingParticles';

export default function SignInPage({ onNavigate }) {
    const [form,      setForm]      = useState({ email: '', password: '' })
    const [showPass,  setShowPass]  = useState(false)
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
            </div>
        </div>

        {/* Right panel — form */}
        <div style={S.rightPanel}>
            <div style={S.formCard}>
                {/* Header */}
                <div style={S.formHead}>
                    <h1 style={S.formH1}>Welcome back</h1>
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
                            placeholder="your@gmail.com"
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

                {/* Divider */}
                <div style={S.divider}>
                    <div style={S.divLine} />
                    <span style={S.divLabel}>OR</span>
                    <div style={S.divLine} />
                </div>

                {/* Social login — compact icon row */}
                <div style={S.socialRow}>
                    {[
                        { Icon: GoogleIcon,    label: 'Continue with Google'    },
                        { Icon: MicrosoftIcon, label: 'Continue with Microsoft' },
                        { Icon: AppleIcon,     label: 'Continue with Apple'     },
                    ].map(({ Icon, label }) => (
                        <button key={label} className="si-social" style={S.socialIconBtn}
                            aria-label={label}
                            onClick={() => onNavigate('lesson')}>
                                <Icon />
                        </button>
                    ))}
                </div>

                {/* Sign up nudge  NOW routes to 'signup' */}
                <p style={S.nudge}> New to Lumina?{' '}
                    <button
                        className="si-newlink"
                        style={S.nudgeLink}
                        onClick={() => onNavigate('signup')}>
                        Create account
                    </button>
                </p>
            </div>
        </div>
    </div>
    {/* Footer note */}
    <p style={S.footNote}>Lumina · Real-time AI teaching for serious learners</p>
    </div>
    )
}
