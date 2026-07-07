import React, { useState, useEffect } from 'react'
import DefaultPage from './pages/Default.jsx'
import SignInPage  from './pages/SignIn.jsx'
import HomePage  from './pages/Home.jsx'
import SignUpPage from './pages/SignUp.jsx'
import LessonPage from './pages/Lesson.jsx'
import CreateCourse from './pages/createCourse.jsx'

const KEYFRAMES = `
@keyframes floatSymbol {
  0%   { transform: translateY(0px)   rotate(0deg);   opacity: var(--sym-op, 0.07); }
  50%  { transform: translateY(-14px) rotate(4deg);   opacity: calc(var(--sym-op, 0.07) * 1.4); }
  100% { transform: translateY(4px)   rotate(-3deg);  opacity: var(--sym-op, 0.07); }
}
@keyframes fadeSlideIn {
  from { opacity: 0; transform: translateY(18px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes fadeIn {
  from { opacity: 0; }
  to   { opacity: 1; }
}
button.cta-hover:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 36px rgba(201,168,76,0.45), 0 2px 8px rgba(0,0,0,0.3);
}
button.cta-hover:hover span.cta-arrow { transform: translateX(5px); }
`

function injectStyles() {
  if (document.getElementById('ma-keyframes')) return
  const style = document.createElement('style')
  style.id = 'ma-keyframes'
  style.textContent = KEYFRAMES
  document.head.appendChild(style)
}

function PageTransition({ children, pageKey }) {
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    setVisible(false)
    const t = setTimeout(() => setVisible(true), 20)
    return () => clearTimeout(t)
  }, [pageKey])
  return (
    <div style={{
      animation: visible ? 'fadeIn 0.35s ease forwards' : 'none',
      opacity: visible ? 1 : 0,
      width: '100%', minHeight: '100vh',
    }}>
      {children}
    </div>
  )
}

// Hash ↔ page mapping
const HASH_MAP = { 
  '#home': 'home', '#signin': 'signin', 
  '#signup': 'signup', '#lesson': 'lesson',
  '#createCourse' : 'createCourse'
}
const PAGE_HASH = { 
  home: '#home', signin: '#signin', 
  signup: '#signup', default: '', lesson: '#lesson',
  createCourse: '#createCourse'
}

export default function App() {
  const [page, setPage] = useState('default')

  const [courseData, setCourseData] = useState(null)

  useEffect(() => { injectStyles() }, [])

  useEffect(() => {
    const onHash = () => {
      const h = window.location.hash
      setPage(HASH_MAP[h] ?? 'default')
    }
    window.addEventListener('hashchange', onHash)
    onHash()
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  // navigate(target)              — plain navigation, no payload
  // navigate(target, payload)     — navigation with course data for LessonPage
  const navigate = (target, payload) => {
    if (payload !== undefined) setCourseData(payload)
    window.location.hash = PAGE_HASH[target] ?? ''
    setPage(target)
  }

  return (
    <PageTransition pageKey={page}>
      {page === 'default'      && <DefaultPage  onNavigate={navigate} />}
      {page === 'signin'       && <SignInPage    onNavigate={navigate} />}
      {page === 'signup'       && <SignUpPage    onNavigate={navigate} />}
      {page === 'home'         && <HomePage      onNavigate={navigate} onBack={() => navigate('default')} />}
      {page === 'lesson'       && <LessonPage    onBack={() => navigate('home')} courseData={courseData} />}
      {page === 'createCourse' && <CreateCourse  onNavigate={navigate} onBack={() => navigate('home')} />}
    </PageTransition>
  )
}

