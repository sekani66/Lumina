import React, { useState, useEffect } from 'react';

// ─── SVG Icons ────────────────────────────────────────────────────────────────
const Icons = {
  Math: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 19.5L14 4H20M4 12H10" />
    </svg>
  ),
  Courses: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" />
    </svg>
  ),
  User: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
    </svg>
  ),
  Sparkles: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
      <path d="M5 3v4M3 5h4" />
    </svg>
  ),
  Target: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <circle cx="12" cy="12" r="6" />
      <circle cx="12" cy="12" r="2" />
    </svg>
  ),
  Book: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" />
    </svg>
  ),
  Star: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
    </svg>
  )
};

// ─── Static Demo Data ─────────────────────────────────────────────────────────
const STUDENT = {
  name:    'Konan',
  role:    'Student · Grade 11',
  level:   8,
  joined:  'Jan 2025',
};

const COURSES = [
  {
    id: 1, subject: 'Mathematics', topic: 'Quadratic Equations',
    color: '#63c8ff', progress: 78, sessions: 5, lastActive: '2 hours ago',
    description: 'Solving quadratic equations using factoring, completing the square and the quadratic formula.',
    tags: ['Algebra', 'Grade 11'],
  },
  {
    id: 2, subject: 'Physics', topic: 'Newtonian Mechanics',
    color: '#a78bfa', progress: 34, sessions: 2, lastActive: '1 day ago',
    description: 'Understanding forces, mass, and acceleration through practical real-world simulations.',
    tags: ['Dynamics', 'Forces'],
  },
  {
    id: 3, subject: 'Engineering', topic: 'Circuit Fundamentals',
    color: '#34d399', progress: 0, sessions: 0, lastActive: 'Never',
    description: 'An introduction to voltage, current, resistance, and basic circuit diagramming.',
    tags: ['Electronics', 'Basics'],
  }
];

// ─── Main Component ───────────────────────────────────────────────────────────
export default function HomePage({ onNavigate }) {
  const [mounted, setMounted] = useState(false);

  // Mount animation trigger
  useEffect(() => { 
    const t = setTimeout(() => setMounted(true), 40);
    return () => clearTimeout(t); 
  }, []);

  return (
    <div style={S.root}>
      <GlobalStyles />
      
      {/* Background Effects */}
      <div style={S.mesh} aria-hidden />
      <div style={S.gridBg} aria-hidden />
      <Particles />

      {/* Top Navigation */}
      <nav style={S.nav}>
        <div style={S.navLogo}>
          <span style={S.logoWord}>Lumina</span>
        </div>

        <div style={S.navCenter}>
          <button style={{ ...S.navTab, color: '#e2f4ff', borderBottom: '2px solid #63c8ff' }}>
            <span style={{ marginRight: 8, display: 'inline-flex', verticalAlign: 'middle' }}><Icons.Courses /></span>
            Dashboard
          </button>
        </div>

        <div style={S.navRight}>
          <button style={S.profileBtn} title="Profile Menu">
            <Icons.User />
          </button>
          <button style={S.navSignOut} onClick={() => onNavigate('signin')}>Sign out</button>
        </div>
      </nav>

      {/* Main Content Layout */}
      <div style={{
        ...S.shell,
        opacity: mounted ? 1 : 0,
        transform: mounted ? 'translateY(0)' : 'translateY(20px)',
        transition: 'opacity 0.6s cubic-bezier(0.16, 1, 0.3, 1), transform 0.6s cubic-bezier(0.16, 1, 0.3, 1)',
      }}>
        
        <div style={S.content}>

          {/* Hero Section */}
          <section style={S.hero}>
            <div style={S.heroGlow} />

            <div style={S.heroLeft}>
              <div style={S.heroBadge}>
                <Icons.Star /> LEVEL {STUDENT.level} SCHOLAR
              </div>

              <h1 style={S.heroTitle}>
                Welcome back, {STUDENT.name}
              </h1>

              <p style={S.heroSubtitle}>
                Continue building your knowledge with Lumina AI. Track your progress, master complex concepts, and explore new subjects at your own pace.
              </p>

              <div style={S.heroActions}>
                <button style={S.newCourseBtn} onClick={() => onNavigate('createCourse')}>
                  + Create Course
                </button>
                <div style={S.infoPill}>
                  <Icons.Book /> {COURSES.length} Active Courses
                </div>
              </div>
            </div>

            <div style={S.heroRight}>
              <div style={S.heroProgressCard}>
                <div style={S.heroProgressHeader}>
                  <Icons.Target /> Current Focus
                </div>
                <div style={S.heroProgressCourse}>
                  Quadratic Equations
                </div>
                <div style={S.heroProgressBar}>
                  <div style={{ ...S.heroProgressFill, width: '78%' }} />
                </div>
                <div style={S.heroProgressValue}>
                  78% Mastered
                </div>
              </div>
            </div>
          </section>

          {/* Stats Overview */}
          <div style={S.progressStats}>
            {[
              { label: 'Overall Completion', val: '37%', color: '#63c8ff' },
              { label: 'Total Sessions', val: '7', color: '#a78bfa' },
              { label: 'Active Courses', val: '3', color: '#34d399' },
              { label: 'Hours Learned', val: '24h', color: '#fbbf24' },
            ].map(s => (
              <div key={s.label} style={S.progressStatCard}>
                <span style={{ ...S.progressStatVal, color: s.color }}>
                  {s.val}
                </span>
                <span style={S.progressStatLabel}>
                  {s.label}
                </span>
              </div>
            ))}
          </div>

          {/* Featured Course */}
          <section style={S.featuredCourse}>
            <div>
              <div style={S.featuredLabel}>
                <Icons.Star /> FEATURED COURSE
              </div>
              <h2 style={S.featuredTitle}>
                Mathematics — Quadratic Equations
              </h2>
              <p style={S.featuredDesc}>
                Continue solving quadratic equations using factoring, completing the square, and the quadratic formula.
              </p>
            </div>
            <button style={S.featuredBtn} onClick={() => onNavigate('lesson')}>
              Resume Learning →
            </button>
          </section>

          <div style={S.sectionEyebrow}>Your Courses</div>

          {/* Courses Grid */}
          <div style={S.coursesGrid}>
            {COURSES.map((course, i) => (
              <CourseCard key={course.id} course={course} idx={i} onNavigate={onNavigate} />
            ))}
          </div>

        </div>
      </div>
    </div>
  );
}

// ─── Course Card Sub-Component ────────────────────────────────────────────────
function CourseCard({ course, idx, onNavigate }) {
  const [hovered, setHovered] = useState(false);
  
  return (
    <div
      style={{
        ...S.courseCard,
        borderColor: hovered ? `${course.color}66` : 'rgba(255,255,255,0.08)',
        boxShadow: hovered ? `0 20px 40px rgba(0,0,0,0.4), 0 0 0 1px ${course.color}22` : '0 8px 24px rgba(0,0,0,0.2)',
        transform: hovered ? 'translateY(-4px)' : 'translateY(0)',
        animation: `fadeUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) ${idx * 0.1}s both`,
      }}
      onMouseEnter={() => setHovered(true)} 
      onMouseLeave={() => setHovered(false)}
    >
      <div style={S.cardTop}>
        <div style={{ ...S.cardIcon, background: `${course.color}18`, color: course.color }}>
          <Icons.Math />
        </div>
        <div style={S.cardMeta}>
          <span style={{ ...S.cardSubject, color: course.color }}>{course.subject}</span>
          <span style={S.cardActive}>{course.lastActive}</span>
        </div>
      </div>

      <div style={S.cardBody}>
        <h3 style={S.cardTopic}>{course.topic}</h3>
        <p style={S.cardDesc}>{course.description}</p>
      </div>

      <div style={S.cardTags}>
        {course.tags.map(t => <span key={t} style={S.cardTag}>{t}</span>)}
        <span style={S.cardSessions}>{course.sessions} session{course.sessions !== 1 ? 's' : ''}</span>
      </div>

      <div style={S.cardProgressWrap}>
        <div style={S.cardProgressRow}>
          <span style={S.cardProgressLabel}>Progress</span>
          <span style={{ ...S.cardProgressPct, color: course.color }}>{course.progress}%</span>
        </div>
        <div style={S.cardProgressTrack}>
          <div style={{ ...S.cardProgressFill, width: `${course.progress}%`, background: `linear-gradient(90deg, ${course.color}66, ${course.color})` }} />
        </div>
      </div>

      <button 
        onClick={() => onNavigate('lesson')}
        style={{
          ...S.cardCta,
          background: hovered ? course.color : 'rgba(255,255,255,0.03)',
          color: hovered ? '#07111f' : course.color,
          borderColor: hovered ? course.color : 'rgba(255,255,255,0.05)',
        }}
      >
        {course.progress === 0 ? 'Start Module' : 'Continue Learning →'}
      </button>
    </div>
  );
}

// ─── Shared Design Elements ───────────────────────────────────────────────────
function Particles() {
  const P = [
    { char: '∫', x: '5%',  y: '12%', sz: 70, d: '0s',   dur: '8s'  },
    { char: 'Σ', x: '91%', y: '18%', sz: 56, d: '1.4s', dur: '9s'  },
    { char: 'π', x: '4%',  y: '68%', sz: 64, d: '0.7s', dur: '7s'  },
    { char: '∇', x: '88%', y: '70%', sz: 50, d: '2.1s', dur: '10s' },
    { char: 'Δ', x: '94%', y: '42%', sz: 46, d: '1.9s', dur: '6s'  },
  ];
  return (
    <div style={{ position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0 }} aria-hidden>
      {P.map((p, i) => (
        <span key={i} style={{
          position: 'absolute', left: p.x, top: p.y, fontSize: p.sz,
          color: '#63c8ff', fontFamily: '"Crimson Pro", Georgia, serif',
          opacity: 0.02, userSelect: 'none',
          animation: `floatUp ${p.dur} ease-in-out ${p.d} infinite`,
        }}>{p.char}</span>
      ))}
    </div>
  );
}

function GlobalStyles() {
  return (
    <style>{`
      @import url('https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,300;0,400;1,300&family=DM+Mono:wght@300;400;500&family=Cabinet+Grotesk:wght@400;500;700;800;900&display=swap');
      *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

      @keyframes floatUp {
        0%,100% { transform: translateY(0) rotate(0deg); opacity: 0.02; }
        50%     { transform: translateY(-18px) rotate(4deg); opacity: 0.04; }
      }
      @keyframes fadeUp {
        from { opacity: 0; transform: translateY(20px); }
        to   { opacity: 1; transform: translateY(0); }
      }
      @keyframes moveGrid {
        0%   { background-position: 0px 0px; }
        100% { background-position: 52px 52px; }
      }
      ul { list-style: none; }
    `}</style>
  );
}

// ─── Design Tokens & Styles ───────────────────────────────────────────────────
const blue  = '#63c8ff';
const dark  = '#050914';
const cardBg= 'rgba(12, 20, 34, 0.6)';
const text1 = '#f1f8ff';
const text2 = 'rgba(241,248,255,0.6)';
const text3 = 'rgba(241,248,255,0.3)';

const S = {
  // Base Layout
  root: {
    minHeight: '100vh', width: '100%', background: dark, color: text1,
    fontFamily: '"Cabinet Grotesk", sans-serif',
    display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden',
  },
  mesh: {
    position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0,
    background: `radial-gradient(ellipse 80% 55% at 20% -10%, rgba(99,200,255,0.08) 0%, transparent 60%), radial-gradient(ellipse 60% 45% at 80% 90%, rgba(120,80,255,0.05) 0%, transparent 60%)`,
  },
  gridBg: {
    position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0,
    backgroundImage: `linear-gradient(rgba(255,255,255,0.015) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.015) 1px, transparent 1px)`,
    backgroundSize: '52px 52px',
    animation: 'moveGrid 30s linear infinite', 
  },

  // Navigation
  nav: {
    position: 'sticky', top: 0, zIndex: 50,
    display: 'flex', alignItems: 'center', padding: '0 32px', height: 64,
    background: 'rgba(5,9,20,0.7)', backdropFilter: 'blur(20px)',
    borderBottom: '1px solid rgba(255,255,255,0.05)', gap: 24,
  },
  navLogo: { display: 'flex', alignItems: 'center', gap: 10, marginRight: 'auto' },
  logoMark: { width: 32, height: 32, borderRadius: 10, background: 'linear-gradient(135deg, #63c8ff, #3a8eff)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 16px rgba(99,200,255,0.2)' },
  logoLetter: { color: '#050914', fontWeight: 900, fontSize: 16 },
  logoWord: { fontSize: 18, fontWeight: 800, color: text1, letterSpacing: '-0.02em' },
  navCenter: { display: 'flex', gap: 16 },
  navTab: {
    background: 'none', border: 'none', display: 'flex', alignItems: 'center',
    padding: '0 10px', height: 64, cursor: 'pointer', fontSize: 14, fontWeight: 600,
    fontFamily: '"Cabinet Grotesk", sans-serif', letterSpacing: '0.01em',
    transition: 'color 0.2s',
  },
  navRight: { display: 'flex', alignItems: 'center', gap: 16 },
  apiPill: {
    display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px', borderRadius: 20,
    background: 'rgba(99,200,255,0.05)', border: '1px solid rgba(99,200,255,0.15)',
    fontSize: 11, fontFamily: '"DM Mono", monospace', color: blue, letterSpacing: '0.05em',
  },
  profileBtn: {
    background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: '50%', width: 36, height: 36, cursor: 'pointer', display: 'flex',
    alignItems: 'center', justifyContent: 'center', color: text1, transition: 'all 0.2s',
  },
  navSignOut: {
    background: 'transparent', border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: 8, padding: '8px 16px', cursor: 'pointer',
    fontSize: 13, color: text2, fontFamily: '"Cabinet Grotesk", sans-serif',
    transition: 'all 0.2s',
  },

  // Content Shell
  shell: { display: 'flex', flex: 1, position: 'relative', zIndex: 2, justifyContent: 'center' },
  content: { flex: 1, maxWidth: 1140, padding: '48px 32px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 32 },

  // Hero Area
  hero: {
    position: 'relative', overflow: 'hidden',
    background: 'linear-gradient(145deg, rgba(16,24,40,0.6), rgba(16,24,40,0.2))',
    border: '1px solid rgba(255,255,255,0.05)',
    borderRadius: 24, padding: 40,
    display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: 40,
    backdropFilter: 'blur(20px)',
  },
  heroGlow: {
    position: 'absolute', top: -100, right: -50, width: 300, height: 300,
    borderRadius: '50%', background: 'rgba(99,200,255,0.1)', filter: 'blur(100px)', zIndex: 0,
  },
  heroLeft: { position: 'relative', zIndex: 2, display: 'flex', flexDirection: 'column', justifyContent: 'center' },
  heroBadge: {
    display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 14px', borderRadius: 999,
    background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)',
    fontSize: 11, fontWeight: 700, letterSpacing: '0.15em', color: text1, width: 'max-content',
  },
  heroTitle: { fontSize: 42, fontWeight: 900, marginTop: 24, letterSpacing: '-0.02em', lineHeight: 1.1 },
  heroSubtitle: { marginTop: 16, maxWidth: 500, color: text2, lineHeight: 1.6, fontSize: 16 },
  heroActions: { display: 'flex', gap: 16, marginTop: 32, alignItems: 'center' },
  newCourseBtn: { 
    background: 'linear-gradient(135deg, #63c8ff, #3a8eff)', border: 'none', borderRadius: 12, 
    padding: '14px 28px', fontSize: 14, fontWeight: 800, color: '#050914', cursor: 'pointer', 
    boxShadow: '0 4px 20px rgba(99,200,255,0.2)', transition: 'transform 0.2s', 
  },
  infoPill: { display: 'flex', alignItems: 'center', gap: 8, padding: '12px 20px', borderRadius: 12, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)', fontSize: 14, color: text2, fontWeight: 500 },
  
  heroRight: { display: 'flex', alignItems: 'center', position: 'relative', zIndex: 2 },
  heroProgressCard: {
    width: '100%', background: 'rgba(5,9,20,0.6)', border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: 20, padding: 28, backdropFilter: 'blur(10px)',
  },
  heroProgressHeader: { display: 'flex', alignItems: 'center', gap: 8, color: text2, fontSize: 12, fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase' },
  heroProgressCourse: { fontSize: 24, fontWeight: 800, marginTop: 12, color: text1 },
  heroProgressBar: { marginTop: 20, height: 6, borderRadius: 999, background: 'rgba(255,255,255,0.05)', overflow: 'hidden' },
  heroProgressFill: { height: '100%', background: 'linear-gradient(90deg, #63c8ff, #a78bfa)', borderRadius: 999 },
  heroProgressValue: { marginTop: 12, color: text2, fontSize: 13, fontWeight: 500, textAlign: 'right' },

  // Grid Sections
  topGrid: { display: 'grid', gridTemplateColumns: '1fr 2.5fr', gap: 24 },
  
  studentHub: { background: cardBg, border: '1px solid rgba(255,255,255,0.05)', borderRadius: 24, padding: 32, display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', backdropFilter: 'blur(10px)' },
  studentAvatar: { width: 80, height: 80, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #63c8ff, #3a8eff)', color: '#050914', fontWeight: 900, fontSize: 32, marginBottom: 20, boxShadow: '0 8px 24px rgba(99,200,255,0.2)' },
  studentName: { fontSize: 22, fontWeight: 800 },
  studentMeta: { color: text2, marginTop: 4, fontSize: 14 },
  studentStats: { display: 'flex', justifyContent: 'center', gap: 24, marginTop: 32, width: '100%' },
  statItem: { display: 'flex', flexDirection: 'column', gap: 4 },
  statDivider: { width: 1, background: 'rgba(255,255,255,0.1)' },

  aiPanel: { background: cardBg, border: '1px solid rgba(255,255,255,0.05)', borderRadius: 24, padding: 32, backdropFilter: 'blur(10px)' },
  aiTitle: { display: 'flex', alignItems: 'center', gap: 10, fontSize: 20, fontWeight: 800, color: text1 },
  aiText: { marginTop: 12, color: text2, fontSize: 15, lineHeight: 1.6 },
  aiSuggestions: { marginTop: 20, display: 'flex', flexDirection: 'column', gap: 12, color: text1, fontSize: 15, fontWeight: 500 },

  // Progress Stats
  progressStats: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 },
  progressStatCard: { background: cardBg, border: '1px solid rgba(255,255,255,0.05)', borderRadius: 16, padding: '28px 24px', display: 'flex', flexDirection: 'column', gap: 8, backdropFilter: 'blur(10px)' },
  progressStatVal: { fontSize: 32, fontWeight: 900, letterSpacing: '-0.02em' },
  progressStatLabel: { fontSize: 12, color: text3, fontFamily: '"DM Mono", monospace', letterSpacing: '0.05em', textTransform: 'uppercase' },
  
  sectionEyebrow: { fontSize: 12, letterSpacing: '0.2em', fontFamily: '"DM Mono", monospace', textTransform: 'uppercase', color: text2, marginBottom: -16, marginTop: 16 },

  // Featured Course
  featuredCourse: { background: 'linear-gradient(135deg, rgba(99,200,255,0.1), rgba(58,142,255,0.02))', border: '1px solid rgba(99,200,255,0.15)', borderRadius: 24, padding: 36, display: 'flex', justifyContent: 'space-between', alignItems: 'center', backdropFilter: 'blur(10px)' },
  featuredLabel: { display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, fontWeight: 700, letterSpacing: '0.15em', color: blue },
  featuredTitle: { marginTop: 16, fontSize: 28, fontWeight: 900, color: text1 },
  featuredDesc: { marginTop: 12, color: text2, maxWidth: 650, fontSize: 16, lineHeight: 1.6 },
  featuredBtn: { borderRadius: 12, padding: '16px 28px', background: 'rgba(99,200,255,0.1)', color: blue, fontWeight: 800, fontSize: 14, cursor: 'pointer', transition: 'all 0.2s', border: '1px solid rgba(99,200,255,0.2)' },

  // Courses Grid
  coursesGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 24 },
  courseCard: { background: cardBg, borderRadius: 20, border: '1px solid rgba(255,255,255,0.05)', padding: '28px', display: 'flex', flexDirection: 'column', gap: 20, transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)', backdropFilter: 'blur(10px)' },
  cardTop: { display: 'flex', alignItems: 'center', gap: 14 },
  cardIcon: { width: 46, height: 46, borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  cardMeta: { display: 'flex', flexDirection: 'column', gap: 4 },
  cardSubject: { fontSize: 12, fontFamily: '"DM Mono", monospace', letterSpacing: '0.1em', textTransform: 'uppercase', fontWeight: 600 },
  cardActive: { fontSize: 12, color: text3, fontFamily: '"DM Mono", monospace' },
  cardBody: { display: 'flex', flexDirection: 'column', gap: 8, flex: 1 },
  cardTopic: { fontSize: 18, fontWeight: 800, color: text1, lineHeight: 1.3 },
  cardDesc: { fontSize: 15, color: text2, lineHeight: 1.5, fontFamily: '"Crimson Pro", Georgia, serif', fontWeight: 300 },
  cardTags: { display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' },
  cardTag: { padding: '4px 12px', borderRadius: 8, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', fontSize: 12, color: text2, fontFamily: '"DM Mono", monospace' },
  cardSessions: { fontSize: 12, color: text3, fontFamily: '"DM Mono", monospace', marginLeft: 'auto' },
  cardProgressWrap: { display: 'flex', flexDirection: 'column', gap: 8, marginTop: 4 },
  cardProgressRow: { display: 'flex', justifyContent: 'space-between' },
  cardProgressLabel: { fontSize: 12, color: text3, fontFamily: '"DM Mono", monospace', letterSpacing: '0.05em' },
  cardProgressPct: { fontSize: 12, fontFamily: '"DM Mono", monospace', fontWeight: 700 },
  cardProgressTrack: { height: 6, background: 'rgba(255,255,255,0.05)', borderRadius: 999, overflow: 'hidden' },
  cardProgressFill: { height: '100%', borderRadius: 999, transition: 'width 0.8s cubic-bezier(0.16, 1, 0.3, 1)' },
  cardCta: { width: '100%', padding: '14px', borderRadius: 12, fontSize: 14, fontWeight: 700, fontFamily: '"Cabinet Grotesk", sans-serif', cursor: 'pointer', transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)', marginTop: 8 },
};