import React, { useState, useEffect, useRef } from 'react'

import { PARTICLES } from '../constants/floatingParticles'
import { FEATURES, STEPS, SUBJECTS, NAV_LINKS } from '../constants/features'
import { LESSON_OPTIONS } from '../constants/lessonOptions'
import { Styles } from '../constants/defaultStyles'


export default function DefaultPage({ onNavigate }) {
  const [scrolled,     setScrolled]     = useState(false)
  const [menuOpen,     setMenuOpen]     = useState(false)
  const [visibleCards, setVisibleCards] = useState([])
  const [previewLines, setPreviewLines] = useState(LESSON_OPTIONS[0])
  const cardRefs = useRef([])

  // Randomize the board lesson on mount
  useEffect(() => {
    const randomIndex = Math.floor(Math.random() * LESSON_OPTIONS.length)
    setPreviewLines(LESSON_OPTIONS[randomIndex])
  }, [])

  // Sticky nav shadow on scroll
  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', handler)
    return () => window.removeEventListener('scroll', handler)
  }, [])

  // Intersection observer stagger-reveal feature cards
  useEffect(() => {
    const obs = new IntersectionObserver(
      entries => {
        entries.forEach(e => {
          if (e.isIntersecting) {
            const idx = parseInt(e.target.dataset.idx)
            setVisibleCards(prev => prev.includes(idx) ? prev : [...prev, idx])
          }
        })
      },
      { threshold: 0.15 }
    )
    cardRefs.current.forEach(el => el && obs.observe(el))
    return () => obs.disconnect()
  }, [])

  return (
    <div style={Styles.root}>

      {/* Global keyframes*/}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,300;0,400;0,600;0,700;1,300;1,600&family=DM+Mono:wght@300;400;500&family=Cabinet+Grotesk:wght@400;500;700;800;900&display=swap');

        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        @keyframes floatUp {
          0%   { transform: translateY(0px) rotate(0deg);   opacity: var(--op); }
          50%  { transform: translateY(-22px) rotate(4deg); opacity: calc(var(--op) * 0.6); }
          100% { transform: translateY(0px) rotate(0deg);   opacity: var(--op); }
        }
        @keyframes fadeSlideUp {
          from { opacity: 0; transform: translateY(32px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes glow {
          0%, 100% { box-shadow: 0 0 32px rgba(99,200,255,0.18), 0 4px 24px rgba(0,0,0,0.5); }
          50%       { box-shadow: 0 0 56px rgba(99,200,255,0.32), 0 4px 24px rgba(0,0,0,0.5); }
        }
        @keyframes pulseRing {
          0%   { transform: scale(1);   opacity: 0.6; }
          100% { transform: scale(1.6); opacity: 0; }
        }
        @keyframes scanLine {
          0%   { top: 0%; }
          100% { top: 100%; }
        }

        .lumina-cta:hover {
          transform: translateY(-2px) scale(1.02);
          box-shadow: 0 8px 40px rgba(99,200,255,0.4), 0 2px 12px rgba(0,0,0,0.4) !important;
        }
        .lumina-cta:active { transform: scale(0.98); }

        .nav-link:hover { color: #63c8ff !important; }

        .feature-card:hover {
          border-color: rgba(99,200,255,0.28) !important;
          transform: translateY(-4px);
          box-shadow: 0 20px 60px rgba(0,0,0,0.4), 0 0 0 1px rgba(99,200,255,0.12) !important;
        }

        .step-node:hover .step-ring { animation: pulseRing 1s ease-out infinite; }

        .secondary-btn:hover {
          background: rgba(99,200,255,0.08) !important;
          border-color: rgba(99,200,255,0.5) !important;
          color: #63c8ff !important;
        }
      `}</style>

      {/* Floating background particles */}
      <div style={Styles.particleLayer} aria-hidden>
        {PARTICLES.map((p, i) => (
          <span key={i} style={{
            position: 'absolute', left: p.x, top: p.y,
            fontSize: p.size, color: '#63c8ff',
            fontFamily: '"Crimson Pro", Georgia, serif',
            '--op': 0.045,
            opacity: 0.045,
            animation: `floatUp ${p.dur} ease-in-out ${p.delay} infinite`,
            userSelect: 'none', pointerEvents: 'none',
          }}>{p.char}</span>
        ))}
      </div>

      {/* Ambient mesh gradient*/}
      <div style={Styles.mesh} aria-hidden />
      <div style={Styles.gridLines} aria-hidden />

      {/* NAV */}
      <nav style={{
        ...Styles.nav,
        background: scrolled ? 'rgba(7,11,20,0.92)' : 'transparent',
        backdropFilter: scrolled ? 'blur(16px)' : 'none',
        borderBottom: scrolled ? '1px solid rgba(99,200,255,0.08)' : '1px solid transparent',
        boxShadow: scrolled ? '0 4px 32px rgba(0,0,0,0.3)' : 'none',
      }}>
        {/* Logo */}
        <div style={Styles.logo}>
          <div style={Styles.logoMark}>
            <span style={Styles.logoMarkInner}>L</span>
          </div>
          <span style={Styles.logoText}>Lumina</span>
          <span style={Styles.logoBadge}>BETA</span>
        </div>

        {/* Desktop links */}
        <div style={Styles.navLinks}>
          {NAV_LINKS.map(l => (
            <a key={l} href={`#${l.toLowerCase().replace(/ /g, '-')}`}
              className="nav-link"
              style={Styles.navLink}
            >{l}</a>
          ))}
        </div>

        {/* Auth buttons */}
        <div style={Styles.navAuth}>
          <button
            className="secondary-btn"
            style={Styles.navSignIn}
            onClick={() => onNavigate('signin')}
          >Sign in</button>
          <button
            className="lumina-cta"
            style={{ ...Styles.navSignUp, transition: 'all 0.2s ease' }}
            onClick={() => onNavigate('board')}
          >Get started free</button>
        </div>

        {/* Mobile hamburger */}
        <button
          style={Styles.hamburger}
          onClick={() => setMenuOpen(o => !o)}
          aria-label="Menu"
        >
          <span style={{ ...Styles.hamBar, opacity: menuOpen ? 0 : 1 }} />
          <span style={Styles.hamBar} />
          <span style={{ ...Styles.hamBar, opacity: menuOpen ? 0 : 1 }} />
        </button>
      </nav>

      {/* Mobile menu */}
      {menuOpen && (
        <div style={Styles.mobileMenu}>
          {NAV_LINKS.map(l => (
            <a key={l} href={`#${l.toLowerCase().replace(/ /g, '-')}`}
              style={Styles.mobileLink}
              onClick={() => setMenuOpen(false)}
            >{l}</a>
          ))}
          <div style={{ height: 1, background: 'rgba(99,200,255,0.1)', margin: '8px 0' }} />
          <button style={{ ...Styles.navSignIn, width: '100%', justifyContent: 'center' }} onClick={() => onNavigate('signin')}>Sign in</button>
          <button
            className="lumina-cta"
            style={{ ...Styles.navSignUp, width: '100%', justifyContent: 'center', transition: 'all 0.2s' }}
            onClick={() => onNavigate('board')}
          >Get started free</button>
        </div>
      )}

      {/* HERO */}
      <section style={Styles.hero}>

        {/* Live badge */}
        <div style={Styles.heroBadge}>
          <span style={Styles.badgePulse} />
          <span style={{ position: 'relative', zIndex: 1 }}>AI Teaching — Live, Not Prerecorded</span>
        </div>

        {/* Headline */}
        <h1 style={Styles.heroH1}>
          The AI that<br />
          <em style={Styles.heroEm}>teaches</em>{' '}
          <span style={Styles.heroAccent}>you</span>
          <br />in real time
        </h1>

        {/* Sub */}
        <p style={Styles.heroSub}>
          Lumina is an AI teaching system that delivers live, structured lessons —
          responding to your questions, filling knowledge gaps, and adapting to
          your pace. Not a chatbot. Not a homework solver. A teacher.
        </p>

        {/* CTAs */}
        <div style={Styles.heroCtas}>
          <button
            className="lumina-cta"
            style={{ ...Styles.ctaPrimary, transition: 'all 0.2s ease', animation: 'glow 3s ease-in-out infinite' }}
            onClick={() => onNavigate('board')}
          >
            Start a free lesson
            <span style={{ fontSize: 20 }}>→</span>
          </button>
          <button className="secondary-btn" style={{ ...Styles.ctaSecondary, transition: 'all 0.2s ease' }}>
            Watch how it works
          </button>
        </div>

        {/* Social proof row */}
        <div style={Styles.socialProof}>
          <div style={Styles.proofAvatars}>
            {['#b0d4ff','#aee8d0','#f0d9b0','#e0b0d4','#c8e0f0'].map((c, i) => (
              <div key={i} style={{ ...Styles.proofAvatar, background: c, marginLeft: i ? -10 : 0 }} />
            ))}
          </div>
          <span style={Styles.proofText}>Trusted by <strong>2,400+</strong> students & educators</span>
        </div>

        {/* Board preview window */}
        <div style={Styles.boardPreview}>
          {/* Scan line animation */}
          <div style={Styles.scanLine} />

          <div style={Styles.boardInner}>
            <div style={Styles.boardHeader}>
              <span style={Styles.boardTitle}>Lumina · Lesson Board</span>
              <span style={Styles.boardLive}>● LIVE</span>
            </div>
            <div style={Styles.boardScreen}>
              {previewLines.map((line, i) => (
                <div key={i} style={{
                  ...Styles.previewLine,
                  animationDelay: `${i * 0.9}s`,
                  opacity: 0,
                  animation: `fadeSlideUp 0.5s ease ${i * 0.9}s forwards`,
                  color: line.color || '#e2f4ff',
                  fontSize: line.size || 14,
                  fontFamily: line.mono ? '"DM Mono", monospace' : '"Crimson Pro", Georgia, serif',
                  fontStyle: line.italic ? 'italic' : 'normal',
                  borderLeft: line.accent ? '2px solid rgba(99,200,255,0.4)' : 'none',
                  paddingLeft: line.accent ? 12 : 0,
                  marginTop: line.gap ? 12 : 0,
                }}>
                  {line.text}
                </div>
              ))}
              {/* Cursor */}
              <div style={Styles.cursor} />
            </div>
          </div>
        </div>

      </section>

      {/* HOW IT WORKS strip  */}
      <section id="how-it-works" style={Styles.howSection}>
        <p style={Styles.sectionEyebrow}>How it works</p>
        <h2 style={Styles.sectionH2}>Four steps to understanding</h2>
        <div style={Styles.stepsRow}>
          {STEPS.map((step, i) => (
            <div key={i} className="step-node" style={Styles.stepNode}>
              <div style={Styles.stepNumWrap}>
                <div className="step-ring" style={Styles.stepRing} />
                <div style={Styles.stepNum}>{step.n}</div>
              </div>
              {i < STEPS.length - 1 && <div style={Styles.stepConnector} />}
              <p style={Styles.stepLabel}>{step.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* FEATURES grid */}
      <section id="features" style={Styles.featuresSection}>
        <p style={Styles.sectionEyebrow}>Why Lumina</p>
        <h2 style={Styles.sectionH2}>Built different, by design</h2>
        <div style={Styles.featuresGrid}>
          {FEATURES.map((f, i) => (
            <div
              key={i}
              ref={el => cardRefs.current[i] = el}
              data-idx={i}
              className="feature-card"
              style={{
                ...Styles.featureCard,
                opacity:   visibleCards.includes(i) ? 1 : 0,
                transform: visibleCards.includes(i) ? 'translateY(0)' : 'translateY(28px)',
                transition: `opacity 0.5s ease ${i * 0.08}s, transform 0.5s ease ${i * 0.08}s, border-color 0.2s, box-shadow 0.2s`,
              }}
            >
              <div style={Styles.featureIcon}>{f.icon}</div>
              <h3 style={Styles.featureTitle}>{f.title}</h3>
              <p style={Styles.featureBody}>{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* NOT / IS */}
      <section style={Styles.claritySection}>
        <div style={Styles.clarityGrid}>
          <div style={Styles.clarityCol}>
            <div style={Styles.clarityLabel}>✗ What Lumina is NOT</div>
            {['A lesson generator', 'A homework solver', 'A traditional chatbot', 'A prerecorded course'].map(t => (
              <div key={t} style={Styles.clarityRow}>
                <span style={{ color: '#ff6b6b', fontWeight: 700, marginRight: 10 }}>✗</span>
                <span style={Styles.clarityText}>{t}</span>
              </div>
            ))}
          </div>
          <div style={Styles.claritySep} />
          <div style={Styles.clarityCol}>
            <div style={{ ...Styles.clarityLabel, color: '#63c8ff' }}>✓ What Lumina IS</div>
            {[
              'A real-time AI teacher',
              'Structured, interactive lessons',
              'A personalised learning journey',
              'Classroom + private tutor + online access',
            ].map(t => (
              <div key={t} style={Styles.clarityRow}>
                <span style={{ color: '#63c8ff', fontWeight: 700, marginRight: 10 }}>✓</span>
                <span style={Styles.clarityText}>{t}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* SUBJECTS  */}
      <section id="subjects" style={Styles.subjectsSection}>
        <p style={Styles.sectionEyebrow}>Subjects</p>
        <h2 style={Styles.sectionH2}>STEM at every level</h2>
        <div style={Styles.subjectsRow}>
          {SUBJECTS.map((s, i) => (
            <div key={i} style={{
              ...Styles.subjectPill,
              opacity: s.includes('soon') ? 0.35 : 1,
              borderStyle: s.includes('soon') ? 'dashed' : 'solid',
            }}>{s}</div>
          ))}
        </div>
      </section>

      {/* BANNER */}
      <section style={Styles.ctaBanner}>
        <div style={Styles.ctaBannerGlow} />
        <p style={Styles.ctaBannerEye}>Ready when you are</p>
        <h2 style={Styles.ctaBannerH}>Your first lesson is free.<br />No card needed.</h2>
        <button
          className="lumina-cta"
          style={{ ...Styles.ctaPrimary, fontSize: 18, padding: '18px 52px', transition: 'all 0.2s ease' }}
          onClick={() => onNavigate('board')}
        >
          Open the Lesson Board →
        </button>
      </section>

      {/* FOOTER */}
      <footer style={Styles.footer}>
        <div style={Styles.footerLogo}>
          <div style={{ ...Styles.logoMark, width: 28, height: 28, fontSize: 14 }}>
            <span style={Styles.logoMarkInner}>L</span>
          </div>
          <span style={{ ...Styles.logoText, fontSize: 16 }}>Lumina</span>
        </div>
        <p style={Styles.footerSub}>
          Real-time AI teaching for mathematics, physics and engineering.
        </p>
        <div style={Styles.footerLinks}>
          {['Privacy', 'Terms', 'Contact', 'Docs'].map(l => (
            <a key={l} href="#" className="nav-link" style={Styles.footerLink}>{l}</a>
          ))}
        </div>
        <p style={Styles.footerCopy}>© 2025 Lumina Education Technologies. All rights reserved.</p>
      </footer>
    </div>
  )
}
