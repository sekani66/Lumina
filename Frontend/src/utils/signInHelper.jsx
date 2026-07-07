// Field wrapper
export function Field({ label, right, children }) {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'rgba(226,244,255,0.55)', letterSpacing: '0.04em' }}>
                    {label}
                </label>
                {right}
            </div>
            {children}
        </div>
    )
}

export function IconSlot({ children }) {
    return (
        <span style={{
            position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)',
            display: 'flex', alignItems: 'center', pointerEvents: 'none', zIndex: 1,
            }}>
            {children}
        </span>
    )
}


export function Spinner() {
    return (
        <span style={{
            display: 'inline-block', width: 16, height: 16,
            border: '2.5px solid rgba(7,17,31,0.28)',
            borderTopColor: '#07111f',
            borderRadius: '50%',
            animation: 'spin 0.72s linear infinite',
            flexShrink: 0,
        }} />
    )
}

