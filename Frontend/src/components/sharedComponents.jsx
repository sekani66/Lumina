import React from "react"


export function Spinner() {
  return (
    <span style={{
      display: 'inline-block', width: 16, height: 16,
      border: '2px solid rgba(5,9,20,0.3)', borderTopColor: '#050914',
      borderRadius: '50%', animation: 'spin 0.7s linear infinite',
    }} />
  )
}

// Spinner shown inside the upload zone and the button while extracting PDF
export function UploadSpinner({ small }) {
  const sz = small ? 14 : 28
  return (
    <span style={{
      display: 'inline-block', width: sz, height: sz,
      border: `${small ? 2 : 3}px solid rgba(99,200,255,0.2)`,
      borderTopColor: '#63c8ff',
      borderRadius: '50%', animation: 'spin 0.9s linear infinite',
    }} />
  )
}

export function ErrorIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0 }}>
      <circle cx="12" cy="12" r="10"/>
      <line x1="12" y1="8" x2="12" y2="12"/>
      <line x1="12" y1="16" x2="12.01" y2="16"/>
    </svg>
  )
}
