import katex from "katex"

export function renderLine(latex) {
  try {
    return {
      html: katex.renderToString(latex, { throwOnError: true, displayMode: false, output: 'html' }),
      latex,
      renderType: 'latex',
    }
  } catch { return null }
}


// ─── parseLatexLines ──────────────────────────────────────────────────────────
export function parseLatexLines(raw) {
  return raw.split('\n').map(l => l.trim()).filter(Boolean).map(renderLine).filter(Boolean)
}

// ─── Board line reveal animation ─────────────────────────────────────────────
export function revealLine(i, ms, setClipPcts, onDone) {
  let raf, start
  const tick = (ts) => {
    if (!start) start = ts
    const raw   = Math.min((ts - start) / ms, 1)
    const eased = raw < 0.5 ? 4 * raw * raw * raw : 1 - Math.pow(-2 * raw + 2, 3) / 2
    setClipPcts(prev => {
      const next = [...prev]
      next[i] = eased * 100
      return next
    })
    if (raw < 1) { raf = requestAnimationFrame(tick) } else { onDone() }
  }
  raf = requestAnimationFrame(tick)
  return () => cancelAnimationFrame(raf)
}

function escapeHtml(v = '') {
  return String(v)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;')
}

export function renderTextLine(text, { isHeading = false } = {}) {
  const safe = escapeHtml(text).replace(/\n/g, '<br/>')
  return {
    html: isHeading
      ? `<span style="font-family:inherit;font-size:11px;font-weight:600;letter-spacing:0.12em;` +
        `text-transform:uppercase;color:rgba(99,200,255,0.65);display:block;` +
        `padding:12px 0 4px;text-align:center;">${safe}</span>`
      : `<div style="font-family:'Crimson Pro',Georgia,serif;font-size:18px;line-height:1.58;` +
        `font-weight:500;letter-spacing:0.01em;color:inherit;display:block;` +
        `max-width:min(820px,100%);text-align:left;white-space:normal;word-break:break-word;">${safe}</div>`,
    isText: true, isHeading, rawText: text, renderType: 'text',
  }
}