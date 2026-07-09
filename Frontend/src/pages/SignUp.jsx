import React, { useState, useEffect } from 'react'
import { PARTICLES } from '../constants/floatingParticles'

// ─── Step 2 data ──────────────────────────────────────────────────────────────
const LEVELS = [
  { id: 'highschool',   label: 'High School'   },
  { id: 'undergrad',    label: 'Undergraduate' },
  { id: 'postgrad',     label: 'Postgraduate'  },
  { id: 'professional', label: 'Professional'  },
  { id: 'selftaught',   label: 'Self-taught'   },
]

const SUBJECTS = [
  { id: 'mathematics', label: 'Mathematics', sym: 'Σ' },
  { id: 'physics',     label: 'Physics',     sym: 'ℏ' },
  { id: 'engineering', label: 'Engineering', sym: '∇' },
]

const GOALS = [
  { id: 'exams',    label: 'Ace Exams',      desc: 'Targeted preparation'     },
  { id: 'mastery',  label: 'Deep Mastery',   desc: 'True understanding'       },
  { id: 'career',   label: 'Career Boost',   desc: 'Applied skills'           },
  { id: 'curiosity',label: 'Pure Curiosity', desc: 'Learn for the love of it' },
]

// ─── Left panel board preview ─────────────────────────────────────────────────
const STRIP_LINES = [
  { text: "LESSON · Newton's Second Law", accent: false },
  { text: 'F = ma',                        big: true     },
  { text: 'GIVEN — m = 3 kg, a = 4 m/s²', accent: false },
  { text: 'F = 3 × 4 = 12 N',             big: true, accent: true },
  { text: 'INTERPRET — net force',         accent: false },
  { text: '∴ F = 12 N  ✓',                big: true     },
]

// ─── Password strength ────────────────────────────────────────────────────────
function passwordStrength(pw) {
  if (!pw) return { label: '', color: 'transparent', pct: 0 }
  let s = 0
  if (pw.length >= 8)          s++
  if (pw.length >= 12)         s++
  if (/[A-Z]/.test(pw))        s++
  if (/[0-9]/.test(pw))        s++
  if (/[^A-Za-z0-9]/.test(pw)) s++
  if (s <= 1) return { label: 'Weak',      color: '#ff6b6b', pct: 20  }
  if (s === 2) return { label: 'Fair',      color: '#ffb347', pct: 40  }
  if (s === 3) return { label: 'Good',      color: '#63c8ff', pct: 65  }
  if (s === 4) return { label: 'Strong',    color: '#4dff91', pct: 82  }
  return              { label: 'Excellent', color: '#4dff91', pct: 100 }
}

// ─── Component ────────────────────────────────────────────────────────────────
export default function SignUpPage({ onNavigate }) {
  const [step,         setStep]         = useState(1)
  const [form,         setForm]         = useState({
    fullName: '', email: '', password: '', confirmPass: '',
    level: '', subjects: [], goal: '',
  })
  const [showPass,     setShowPass]     = useState(false)
  const [showConfirm,  setShowConfirm]  = useState(false)
  const [focused,      setFocused]      = useState(null)
  const [mounted,      setMounted]      = useState(false)
  const [loading,      setLoading]      = useState(false)
  const [errors,       setErrors]       = useState({})

  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 40)
    return () => clearTimeout(t)
  }, [])

  const set = f => e => setForm(p => ({ ...p, [f]: e.target.value }))

  const toggleSubject = id => setForm(p => ({
    ...p,
    subjects: p.subjects.includes(id)
      ? p.subjects.filter(s => s !== id)
      : [...p.subjects, id],
  }))

  const goNext = e => {
    e.preventDefault()
    // Validation removed for testing purposes
    setErrors({})
    setStep(2)
  }

  const handleSubmit = async e => {
    e.preventDefault()
    // Validation removed for testing purposes
    setErrors({})
    setLoading(true)
    await new Promise(r => setTimeout(r, 1050))
    onNavigate('lesson')
  }

  const pwStr = passwordStrength(form.password)

  return (
    <div style={S.root}>

      {/* ── Keyframes + input styles ─────────────────────────────────────────── */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,300;0,400;0,600;1,300;1,600&family=DM+Mono:wght@300;400;500&family=Cabinet+Grotesk:wght@400;500;700;800;900&display=swap');
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        @keyframes floatUp {
          0%,100% { transform: translateY(0) rotate(0deg);     opacity: 0.04; }
          50%      { transform: translateY(-20px) rotate(5deg); opacity: 0.018; }
        }
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(22px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        @keyframes blink {
          0%,100% { opacity: 1; }
          50%      { opacity: 0; }
        }
        @keyframes glowPulse {
          0%,100% { box-shadow: 0 0 28px rgba(99,200,255,0.15), 0 4px 24px rgba(0,0,0,0.5); }
          50%      { box-shadow: 0 0 48px rgba(99,200,255,0.28), 0 4px 24px rgba(0,0,0,0.5); }
        }
        @keyframes stepSlide {
          from { opacity: 0; transform: translateX(18px); }
          to   { opacity: 1; transform: translateX(0); }
        }

        /* ── Inputs ── */
        .su-input {
          width: 100%;
          background: rgba(99,200,255,0.038);
          border: 1.5px solid rgba(99,200,255,0.13);
          border-radius: 11px;
          padding: 14px 46px 14px 46px;
          font-size: 14.5px;
          color: #e2f4ff;
          outline: none;
          font-family: 'Cabinet Grotesk', sans-serif;
          transition: border-color 0.2s, background 0.2s, box-shadow 0.2s;
          caret-color: #63c8ff;
          letter-spacing: 0.01em;
        }
        .su-input::placeholder { color: rgba(226,244,255,0.22); font-weight: 400; }
        .su-input:focus {
          border-color: rgba(99,200,255,0.52);
          background: rgba(99,200,255,0.07);
          box-shadow: 0 0 0 3.5px rgba(99,200,255,0.09), 0 2px 14px rgba(0,0,0,0.28);
        }
        .su-input:-webkit-autofill {
          -webkit-box-shadow: 0 0 0 100px #0b1424 inset;
          -webkit-text-fill-color: #e2f4ff;
          caret-color: #63c8ff;
        }
        .su-input-error {
          border-color: rgba(255,107,107,0.42) !important;
          background: rgba(255,107,107,0.03) !important;
        }

        /* ── Social buttons ── */
        .su-social:hover {
          border-color: rgba(99,200,255,0.32) !important;
          background: rgba(99,200,255,0.07) !important;
          color: #e2f4ff !important;
        }

        /* ── Submit ── */
        .su-submit:not(:disabled):hover {
          transform: translateY(-2px);
          box-shadow: 0 10px 38px rgba(99,200,255,0.38), 0 2px 14px rgba(0,0,0,0.4) !important;
        }
        .su-submit:not(:disabled):active { transform: scale(0.98); }

        /* ── Misc ── */
        .su-back:hover      { color: #63c8ff !important; }
        .su-backstep:hover  { color: rgba(226,244,255,0.5) !important; }
        .su-eyebtn:hover    { opacity: 1 !important; }
        .su-signin:hover    { text-decoration: underline; color: #88d8ff !important; }

        /* ── Pill / goal selectors ── */
        .su-pill:hover {
          border-color: rgba(99,200,255,0.38) !important;
          background: rgba(99,200,255,0.08) !important;
        }
        .su-goal:hover {
          border-color: rgba(99,200,255,0.32) !important;
          background: rgba(99,200,255,0.06) !important;
        }
      `}</style>

      {/* ── Background layers ─────────────────────────────────────────────────── */}
      <div style={S.mesh}          aria-hidden />
      <div style={S.grid}          aria-hidden />

      {/* ── Particles ─────────────────────────────────────────────────────────── */}
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

      {/* ── Back link ─────────────────────────────────────────────────────────── */}
      <button className="su-back" onClick={() => onNavigate('signin')} style={S.backLink}>
        <ArrowLeft /> Back to Sign In
      </button>

      {/* ── Main shell ────────────────────────────────────────────────────────── */}
      <div style={{
        ...S.shell,
        opacity:    mounted ? 1 : 0,
        transform:  mounted ? 'translateY(0)' : 'translateY(30px)',
        transition: 'opacity 0.5s ease, transform 0.5s ease',
      }}>

        {/* ─── Left panel — branding ─────────────────────────────────────────── */}
        <div style={S.leftPanel}>
          <div style={S.leftInner}>

            {/* Logo */}
            <div style={S.logoRow}>
              <div style={S.logoMark}><span style={S.logoLetter}>L</span></div>
              <span style={S.logoWord}>Lumina</span>
            </div>

            {/* Headline */}
            <h2 style={S.leftHeading}>
              Your AI tutor<br />
              <em style={S.leftEm}>awaits</em> — start<br />
              <span style={S.leftAccent}>learning today.</span>
            </h2>

            <p style={S.leftSub}>
              Create your profile in under two minutes and begin
              your first live, personalised lesson immediately.
            </p>

            {/* Stats */}
            <div style={S.statsRow}>
              {[
                { n: '< 2 min', l: 'Setup'      },
                { n: 'Day 1',   l: 'First Lesson'},
                { n: '∞',       l: 'Patience'   },
              ].map(s => (
                <div key={s.l} style={S.statBlock}>
                  <span style={S.statNum}>{s.n}</span>
                  <span style={S.statLabel}>{s.l}</span>
                </div>
              ))}
            </div>

            {/* Board preview strip */}
            <div style={S.boardStrip}>
              {STRIP_LINES.map((line, i) => (
                <div key={i} style={{
                  ...S.stripLine,
                  opacity: 0,
                  animation: `fadeUp 0.45s ease ${i * 1.05 + 0.4}s forwards`,
                  color:         line.accent ? '#63c8ff' : 'rgba(226,244,255,0.55)',
                  fontSize:      line.big    ? 17 : 11,
                  fontFamily:    line.big    ? '"Crimson Pro", serif' : '"DM Mono", monospace',
                  letterSpacing: line.big    ? 0 : '0.06em',
                  borderLeft:    line.big    ? '2px solid rgba(99,200,255,0.35)' : 'none',
                  paddingLeft:   line.big    ? 10 : 0,
                }}>{line.text}</div>
              ))}
              <div style={S.stripCursor} />
            </div>

          </div>
        </div>

        {/* ─── Right panel — form ────────────────────────────────────────────── */}
        <div style={S.rightPanel}>
          <div style={S.formCard}>

            {/* ── Step progress indicator ──────────────────────────────────── */}
            <div style={S.stepBar}>
              <div style={S.stepTrack}>
                <div style={{
                  ...S.stepFill,
                  width: step === 1 ? '50%' : '100%',
                  transition: 'width 0.45s cubic-bezier(0.4,0,0.2,1)',
                }} />
              </div>
              <div style={S.stepLabels}>
                <span style={{
                  ...S.stepLabelText,
                  color: step === 1 ? '#63c8ff' : 'rgba(226,244,255,0.28)',
                }}>01 · Account</span>
                <span style={{ color: 'rgba(226,244,255,0.16)', fontSize: 10 }}>——</span>
                <span style={{
                  ...S.stepLabelText,
                  color: step === 2 ? '#63c8ff' : 'rgba(226,244,255,0.28)',
                }}>02 · Learning Profile</span>
              </div>
            </div>

            {/* ── Form header ──────────────────────────────────────────────── */}
            <div style={S.formHead}>
              {step === 1 ? (
                <>
                  <h1 style={S.formH1}>Create your account</h1>
                  <p style={S.formSub}>Join thousands of serious STEM learners</p>
                </>
              ) : (
                <div style={{ animation: 'stepSlide 0.32s ease forwards' }}>
                  <h1 style={S.formH1}>Your learning profile</h1>
                  <p style={S.formSub}>Help Lumina personalise every lesson for you</p>
                </div>
              )}
            </div>

            {/* ═══ STEP 1 ══════════════════════════════════════════════════════ */}
            {step === 1 && (
              <>
                {/* Social sign-up */}
                <div style={S.socialCol}>
                  {[
                    { Icon: GoogleIcon,    label: 'Continue with Google'    },
                    { Icon: MicrosoftIcon, label: 'Continue with Microsoft' },
                  ].map(({ Icon, label }) => (
                    <button
                      key={label}
                      className="su-social"
                      style={S.socialBtn}
                      onClick={() => onNavigate('lesson')}
                    >
                      <Icon /><span>{label}</span>
                    </button>
                  ))}
                </div>

                {/* Divider */}
                <div style={S.divider}>
                  <div style={S.divLine} />
                  <span style={S.divLabel}>or continue with email</span>
                  <div style={S.divLine} />
                </div>

                {/* Form fields */}
                <form onSubmit={goNext} style={S.form} noValidate>

                  {/* Full name */}
                  <Field label="Full name" error={errors.fullName}>
                    <div style={S.inputWrap}>
                      <IconSlot><PersonIcon active={focused === 'fullName'} /></IconSlot>
                      <input
                        className={`su-input${errors.fullName ? ' su-input-error' : ''}`}
                        type="text"
                        placeholder="Ada Lovelace"
                        value={form.fullName}
                        onChange={set('fullName')}
                        onFocus={() => setFocused('fullName')}
                        onBlur={() => setFocused(null)}
                        autoComplete="name"
                      />
                    </div>
                  </Field>

                  {/* Email */}
                  <Field label="Email address" error={errors.email}>
                    <div style={S.inputWrap}>
                      <IconSlot><MailIcon active={focused === 'email'} /></IconSlot>
                      <input
                        className={`su-input${errors.email ? ' su-input-error' : ''}`}
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
                  <Field label="Password" error={errors.password}>
                    <div style={S.inputWrap}>
                      <IconSlot><LockIcon active={focused === 'password'} /></IconSlot>
                      <input
                        className={`su-input${errors.password ? ' su-input-error' : ''}`}
                        type={showPass ? 'text' : 'password'}
                        placeholder="Create a strong password"
                        value={form.password}
                        onChange={set('password')}
                        onFocus={() => setFocused('password')}
                        onBlur={() => setFocused(null)}
                        autoComplete="new-password"
                        style={{ paddingRight: 46 }}
                      />
                      <button
                        type="button"
                        className="su-eyebtn"
                        onClick={() => setShowPass(v => !v)}
                        style={S.eyeBtn}
                        aria-label={showPass ? 'Hide password' : 'Show password'}
                      >
                        {showPass ? <EyeOffIcon /> : <EyeIcon />}
                      </button>
                    </div>
                    {/* Strength meter */}
                    {form.password && (
                      <div style={S.pwRow}>
                        <div style={S.pwTrack}>
                          <div style={{
                            ...S.pwFill,
                            width: `${pwStr.pct}%`,
                            background: pwStr.color,
                          }} />
                        </div>
                        <span style={{ ...S.pwLabel, color: pwStr.color }}>{pwStr.label}</span>
                      </div>
                    )}
                  </Field>

                  {/* Confirm password */}
                  <Field label="Confirm password" error={errors.confirmPass}>
                    <div style={S.inputWrap}>
                      <IconSlot><ShieldIcon active={focused === 'confirmPass'} /></IconSlot>
                      <input
                        className={`su-input${errors.confirmPass ? ' su-input-error' : ''}`}
                        type={showConfirm ? 'text' : 'password'}
                        placeholder="Repeat your password"
                        value={form.confirmPass}
                        onChange={set('confirmPass')}
                        onFocus={() => setFocused('confirmPass')}
                        onBlur={() => setFocused(null)}
                        autoComplete="new-password"
                        style={{ paddingRight: 46 }}
                      />
                      <button
                        type="button"
                        className="su-eyebtn"
                        onClick={() => setShowConfirm(v => !v)}
                        style={S.eyeBtn}
                        aria-label={showConfirm ? 'Hide confirm' : 'Show confirm'}
                      >
                        {showConfirm ? <EyeOffIcon /> : <EyeIcon />}
                      </button>
                    </div>
                  </Field>

                  <button
                    type="submit"
                    className="su-submit"
                    style={{
                      ...S.submitBtn,
                      background: 'linear-gradient(135deg, #63c8ff 0%, #3a8eff 100%)',
                      color: '#07111f',
                      cursor: 'pointer',
                      animation: 'glowPulse 3s ease-in-out infinite',
                      transition: 'transform 0.18s ease, box-shadow 0.18s ease',
                    }}
                  >
                    Continue <span style={{ fontSize: 18 }}>→</span>
                  </button>

                </form>
              </>
            )}

            {/* ═══ STEP 2 ══════════════════════════════════════════════════════ */}
            {step === 2 && (
              <form
                onSubmit={handleSubmit}
                style={{ ...S.form, gap: 18, animation: 'stepSlide 0.32s ease forwards' }}
                noValidate
              >

                {/* Academic level */}
                <div>
                  <SectionLabel>Academic level</SectionLabel>
                  <div style={S.pillGrid}>
                    {LEVELS.map(l => {
                      const on = form.level === l.id
                      return (
                        <button
                          key={l.id}
                          type="button"
                          className="su-pill"
                          onClick={() => setForm(p => ({ ...p, level: l.id }))}
                          style={{
                            ...S.pill,
                            borderColor: on ? '#63c8ff' : 'rgba(99,200,255,0.14)',
                            background:  on ? 'rgba(99,200,255,0.13)' : 'rgba(99,200,255,0.03)',
                            color:       on ? '#e2f4ff' : 'rgba(226,244,255,0.55)',
                          }}
                        >{l.label}</button>
                      )
                    })}
                  </div>
                  {errors.level && <ErrMsg>{errors.level}</ErrMsg>}
                </div>

                {/* Subjects */}
                <div>
                  <SectionLabel>
                    Subjects of interest{' '}
                    <span style={{ color: 'rgba(226,244,255,0.28)', fontWeight: 400 }}>
                      (choose all that apply)
                    </span>
                  </SectionLabel>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    {SUBJECTS.map(s => {
                      const on = form.subjects.includes(s.id)
                      return (
                        <button
                          key={s.id}
                          type="button"
                          className="su-pill"
                          onClick={() => toggleSubject(s.id)}
                          style={{
                            ...S.pill,
                            display: 'flex', alignItems: 'center', gap: 6,
                            borderColor: on ? '#63c8ff' : 'rgba(99,200,255,0.14)',
                            background:  on ? 'rgba(99,200,255,0.13)' : 'rgba(99,200,255,0.03)',
                            color:       on ? '#e2f4ff' : 'rgba(226,244,255,0.55)',
                          }}
                        >
                          <span style={{
                            fontFamily: '"Crimson Pro", serif',
                            fontSize: 15,
                            color: on ? '#63c8ff' : 'rgba(226,244,255,0.28)',
                          }}>{s.sym}</span>
                          {s.label}
                          {on && <MiniCheck />}
                        </button>
                      )
                    })}
                  </div>
                  {errors.subjects && <ErrMsg>{errors.subjects}</ErrMsg>}
                </div>

                {/* Learning goal */}
                <div>
                  <SectionLabel>Primary learning goal</SectionLabel>
                  <div style={S.goalGrid}>
                    {GOALS.map(g => {
                      const on = form.goal === g.id
                      return (
                        <button
                          key={g.id}
                          type="button"
                          className="su-goal"
                          onClick={() => setForm(p => ({ ...p, goal: g.id }))}
                          style={{
                            ...S.goalCard,
                            borderColor: on ? '#63c8ff' : 'rgba(99,200,255,0.12)',
                            background:  on ? 'rgba(99,200,255,0.10)' : 'rgba(99,200,255,0.025)',
                          }}
                        >
                          <span style={{
                            fontSize: 12.5, fontWeight: 700,
                            color: on ? '#e2f4ff' : 'rgba(226,244,255,0.6)',
                          }}>{g.label}</span>
                          <span style={{
                            fontSize: 10.5,
                            color: on ? 'rgba(226,244,255,0.45)' : 'rgba(226,244,255,0.25)',
                            fontFamily: '"DM Mono", monospace',
                            letterSpacing: '0.04em',
                          }}>{g.desc}</span>
                        </button>
                      )
                    })}
                  </div>
                  {errors.goal && <ErrMsg>{errors.goal}</ErrMsg>}
                </div>

                {/* CTA */}
                <button
                  type="submit"
                  className="su-submit"
                  disabled={loading}
                  style={{
                    ...S.submitBtn,
                    marginTop: 2,
                    background: loading
                      ? 'rgba(99,200,255,0.28)'
                      : 'linear-gradient(135deg, #63c8ff 0%, #3a8eff 100%)',
                    color:  loading ? 'rgba(7,17,31,0.55)' : '#07111f',
                    cursor: loading ? 'not-allowed' : 'pointer',
                    animation: loading ? 'none' : 'glowPulse 3s ease-in-out infinite',
                    transition: 'transform 0.18s ease, box-shadow 0.18s ease, background 0.3s',
                  }}
                >
                  {loading
                    ? <><Spinner /> Setting up your account…</>
                    : <>Begin Learning <span style={{ fontSize: 18 }}>→</span></>
                  }
                </button>

                {/* Back to step 1 */}
                <button
                  type="button"
                  className="su-backstep"
                  onClick={() => { setStep(1); setErrors({}) }}
                  style={S.backStepBtn}
                >
                  ← Back to account details
                </button>

              </form>
            )}

            {/* ── Sign in nudge ─────────────────────────────────────────────── */}
            <p style={S.nudge}>
              Already have an account?{' '}
              <button
                className="su-signin"
                style={S.nudgeLink}
                onClick={() => onNavigate('signin')}
              >
                Sign in
              </button>
            </p>

            {/* ── Legal ─────────────────────────────────────────────────────── */}
            <p style={S.legal}>
              By creating an account you agree to our{' '}
              <a href="#" style={S.legalLink}>Terms of Service</a>
              {' '}and{' '}
              <a href="#" style={S.legalLink}>Privacy Policy</a>.
            </p>

          </div>
        </div>
      </div>

      <p style={S.footNote}>Lumina · Real-time AI teaching for serious learners</p>

    </div>
  )
}

// ─── Helper components ────────────────────────────────────────────────────────
function Field({ label, error, children }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <label style={{
        fontSize: 12, fontWeight: 600,
        color: 'rgba(226,244,255,0.55)',
        letterSpacing: '0.04em',
      }}>
        {label}
      </label>
      {children}
      {error && <ErrMsg>{error}</ErrMsg>}
    </div>
  )
}

function SectionLabel({ children }) {
  return (
    <div style={{
      fontSize: 12, fontWeight: 600,
      color: 'rgba(226,244,255,0.55)',
      letterSpacing: '0.04em',
      marginBottom: 8,
    }}>
    {children}
    </div>
  )
}

function ErrMsg({ children }) {
  return (
    <span style={{
      fontSize: 11, color: '#ff8c8c',
      fontFamily: '"DM Mono", monospace',
      letterSpacing: '0.03em', marginTop: 3,
    }}>
      {children}
    </span>
  )
}

function IconSlot({ children }) {
  return (
    <span style={{
      position: 'absolute', left: 14, top: '50%',
      transform: 'translateY(-50%)',
      display: 'flex', alignItems: 'center',
      pointerEvents: 'none', zIndex: 1,
    }}>
      {children}
    </span>
  )
}

function MiniCheck() {
  return (
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none"
      stroke="#63c8ff" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
  )
}

function Spinner() {
  return (
    <span style={{
      display: 'inline-block',
      width: 16, height: 16,
      border: '2.5px solid rgba(7,17,31,0.28)',
      borderTopColor: '#07111f',
      borderRadius: '50%',
      animation: 'spin 0.72s linear infinite',
      flexShrink: 0,
    }} />
  )
}

// ─── SVG icons ────────────────────────────────────────────────────────────────
const ic  = active => active ? '#63c8ff' : 'rgba(226,244,255,0.3)'
const sw  = 1.8

const ArrowLeft = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="m15 18-6-6 6-6"/>
  </svg>
)

const PersonIcon = ({ active }) => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
    stroke={ic(active)} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
    <circle cx="12" cy="7" r="4"/>
  </svg>
)

const MailIcon = ({ active }) => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
    stroke={ic(active)} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="4" width="20" height="16" rx="2"/>
    <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>
  </svg>
)

const LockIcon = ({ active }) => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
    stroke={ic(active)} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="11" width="18" height="11" rx="2"/>
    <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
  </svg>
)

const ShieldIcon = ({ active }) => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
    stroke={ic(active)} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
  </svg>
)

const EyeIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
    stroke="rgba(226,244,255,0.3)" strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
    <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z"/>
    <circle cx="12" cy="12" r="3"/>
  </svg>
)

const EyeOffIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
    stroke="rgba(99,200,255,0.65)" strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
    <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
    <line x1="1" y1="1" x2="23" y2="23"/>
  </svg>
)

const GoogleIcon = () => (
  <svg width="17" height="17" viewBox="0 0 24 24">
    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
  </svg>
)

const MicrosoftIcon = () => (
  <svg width="17" height="17" viewBox="0 0 24 24">
    <rect x="1"  y="1"  width="10" height="10" fill="#f25022"/>
    <rect x="13" y="1"  width="10" height="10" fill="#7fba00"/>
    <rect x="1"  y="13" width="10" height="10" fill="#00a4ef"/>
    <rect x="13" y="13" width="10" height="10" fill="#ffb900"/>
  </svg>
)

// ─── Styles ───────────────────────────────────────────────────────────────────
const blue  = '#63c8ff'
const dark  = '#070b14'
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
      radial-gradient(ellipse 70% 60% at 85% 20%, rgba(99,200,255,0.08) 0%, transparent 60%),
      radial-gradient(ellipse 55% 45% at 15% 78%, rgba(120,80,255,0.07) 0%, transparent 60%)
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

  // ── Shell ──
  shell: {
    position: 'relative', zIndex: 2,
    display: 'flex', width: '100%', maxWidth: 1000,
    minHeight: 640,
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
  statNum: { fontSize: 20, fontWeight: 800, color: blue, letterSpacing: '-0.02em' },
  statLabel: { fontSize: 10, color: text3, fontFamily: '"DM Mono", monospace', letterSpacing: '0.12em' },
  boardStrip: {
    background: 'rgba(7,11,20,0.55)',
    border: '1px solid rgba(99,200,255,0.1)',
    borderRadius: 12,
    padding: '16px 18px 18px',
    display: 'flex', flexDirection: 'column', gap: 5,
    marginTop: 'auto', overflow: 'hidden', position: 'relative',
  },
  stripLine: { lineHeight: 1.5 },
  stripCursor: {
    width: 2, height: 15, background: blue,
    borderRadius: 1, marginTop: 4,
    animation: 'blink 1.1s ease-in-out infinite',
  },

  // ── Right panel ──
  rightPanel: {
    flex: 1,
    background: 'linear-gradient(160deg, #0c1422 0%, #080e1a 100%)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    padding: '40px 44px',
    overflowY: 'auto',
  },
  formCard: {
    width: '100%', maxWidth: 380,
    display: 'flex', flexDirection: 'column', gap: 18,
  },

  // ── Step bar ──
  stepBar: { display: 'flex', flexDirection: 'column', gap: 7 },
  stepTrack: {
    height: 3, borderRadius: 2,
    background: 'rgba(99,200,255,0.1)',
    overflow: 'hidden',
  },
  stepFill: {
    height: '100%', borderRadius: 2,
    background: 'linear-gradient(90deg, #63c8ff, #3a8eff)',
  },
  stepLabels: {
    display: 'flex', gap: 8, alignItems: 'center',
    fontSize: 10, fontFamily: '"DM Mono", monospace',
    letterSpacing: '0.07em',
  },
  stepLabelText: { transition: 'color 0.3s' },

  // ── Form header ──
  formHead: { display: 'flex', flexDirection: 'column', gap: 5 },
  formH1: {
    fontSize: 25, fontWeight: 900, color: text1,
    letterSpacing: '-0.03em', lineHeight: 1.1,
  },
  formSub: {
    fontSize: 14, color: text2,
    fontFamily: '"Crimson Pro", Georgia, serif',
    fontWeight: 300,
  },

  // ── Social ──
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
  divLabel: {
    fontSize: 10.5, color: text3,
    fontFamily: '"DM Mono", monospace',
    letterSpacing: '0.07em', whiteSpace: 'nowrap',
  },

  // ── Form fields ──
  form: { display: 'flex', flexDirection: 'column', gap: 13 },
  inputWrap: { position: 'relative', display: 'flex', alignItems: 'center' },
  eyeBtn: {
    position: 'absolute', right: 14, zIndex: 1,
    background: 'none', border: 'none', cursor: 'pointer',
    display: 'flex', alignItems: 'center',
    opacity: 0.7, transition: 'opacity 0.18s', padding: 0,
  },

  // ── Password strength ──
  pwRow: { display: 'flex', alignItems: 'center', gap: 8, marginTop: 5 },
  pwTrack: {
    flex: 1, height: 3, borderRadius: 2,
    background: 'rgba(255,255,255,0.06)', overflow: 'hidden',
  },
  pwFill: {
    height: '100%', borderRadius: 2,
    transition: 'width 0.35s ease, background 0.35s ease',
  },
  pwLabel: {
    fontSize: 10, fontFamily: '"DM Mono", monospace',
    letterSpacing: '0.06em', flexShrink: 0,
    transition: 'color 0.35s ease',
  },

  // ── Step 2 selectors ──
  pillGrid: { display: 'flex', flexWrap: 'wrap', gap: 7 },
  pill: {
    padding: '7px 14px', borderRadius: 30,
    border: '1.5px solid rgba(99,200,255,0.14)',
    fontSize: 12.5, fontWeight: 600,
    cursor: 'pointer', fontFamily: '"Cabinet Grotesk", sans-serif',
    transition: 'border-color 0.18s, background 0.18s, color 0.18s',
    background: 'none',
  },
  goalGrid: {
    display: 'grid', gridTemplateColumns: '1fr 1fr',
    gap: 8,
  },
  goalCard: {
    padding: '11px 13px', borderRadius: 10,
    border: '1.5px solid rgba(99,200,255,0.12)',
    display: 'flex', flexDirection: 'column', gap: 3, textAlign: 'left',
    cursor: 'pointer', fontFamily: '"Cabinet Grotesk", sans-serif',
    transition: 'border-color 0.18s, background 0.18s',
    background: 'none',
  },

  // ── Buttons ──
  submitBtn: {
    width: '100%', padding: '14px',
    borderRadius: 11, border: 'none',
    fontSize: 14.5, fontWeight: 800,
    fontFamily: '"Cabinet Grotesk", sans-serif',
    letterSpacing: '0.02em',
    display: 'flex', alignItems: 'center',
    justifyContent: 'center', gap: 9,
  },
  backStepBtn: {
    background: 'none', border: 'none', cursor: 'pointer',
    color: text3, fontSize: 11.5,
    fontFamily: '"DM Mono", monospace',
    letterSpacing: '0.04em',
    textAlign: 'center',
    transition: 'color 0.18s', padding: '3px 0',
  },

  // ── Footer ──
  nudge: { textAlign: 'center', fontSize: 13, color: text2 },
  nudgeLink: {
    background: 'none', border: 'none', cursor: 'pointer',
    color: blue, fontWeight: 700, fontSize: 13,
    fontFamily: '"Cabinet Grotesk", sans-serif',
    transition: 'color 0.18s',
  },
  legal: {
    textAlign: 'center', fontSize: 10.5, color: text3,
    fontFamily: '"DM Mono", monospace', lineHeight: 1.6,
  },
  legalLink: { color: text3, textDecoration: 'underline', textUnderlineOffset: 3 },
  footNote: {
    position: 'relative', zIndex: 2,
    marginTop: 28, fontSize: 10.5,
    color: 'rgba(226,244,255,0.14)',
    fontFamily: '"DM Mono", monospace', letterSpacing: '0.1em',
  },
}