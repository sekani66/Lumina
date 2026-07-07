export function revealLine(i, ms, setClipPcts, onDone) {
    let raf, start

    const tick = (ts) => {
        if (!start) start = ts
        const raw = Math.min((ts - start) / ms, 1)
        const eased = raw < 0.5 ? 4 * raw * raw * raw : 1 - Math.pow(-2 * raw + 2, 3) / 2
        setClipPcts(prev => {
            const next = [...prev]
            next[i] = eased * 100
            return next
        })
    if (raw < 1) { raf = requestAnimationFrame(tick) }
    else         
        { onDone() }
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
}
