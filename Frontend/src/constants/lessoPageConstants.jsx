export const LESSON_OPTIONS = [
    [
        { text: 'LESSON · Quadratic Equations',      color: 'rgba(99,200,255,0.5)', size: 10, mono: true },
        { text: 'Let\'s solve 2x² + 6x + 4 = 0',     color: '#c8e8ff', size: 15, italic: true, gap: true },
        { text: 'Step 1 — divide every term by 2',   color: 'rgba(200,232,255,0.5)', size: 12, mono: true, gap: true },
        { text: 'x² + 3x + 2 = 0',                   color: '#ffffff', size: 22, accent: true, gap: true },
        { text: 'Step 2 — factor the left-hand side',color: 'rgba(200,232,255,0.5)', size: 12, mono: true, gap: true },
        { text: '(x + 1)(x + 2) = 0',                color: '#ffffff', size: 22, accent: true },
        { text: 'Therefore  x = −1  or  x = −2',     color: '#63c8ff', size: 16, italic: true, gap: true },
    ],
    [
        { text: 'LESSON · Kinematics',                  color: 'rgba(99,200,255,0.5)', size: 10, mono: true },
        { text: 'Find the final velocity: v = u + at',  color: '#c8e8ff', size: 15, italic: true, gap: true },
        { text: 'Given: u = 0 m/s, a = 9.8 m/s², t = 3s',color: 'rgba(200,232,255,0.5)', size: 12, mono: true, gap: true },
        { text: 'v = 0 + (9.8)(3)',                     color: '#ffffff', size: 22, accent: true, gap: true },
        { text: 'Calculate the product',                color: 'rgba(200,232,255,0.5)', size: 12, mono: true, gap: true },
        { text: 'v = 29.4',                             color: '#ffffff', size: 22, accent: true },
        { text: 'Therefore final velocity is 29.4 m/s', color: '#63c8ff', size: 16, italic: true, gap: true },
    ],
    [
        { text: 'LESSON · Calculus',                    color: 'rgba(99,200,255,0.5)', size: 10, mono: true },
        { text: 'Find the derivative of f(x) = x³ + 4x',color: '#c8e8ff', size: 15, italic: true, gap: true },
        { text: 'Step 1 — apply the power rule',        color: 'rgba(200,232,255,0.5)', size: 12, mono: true, gap: true },
        { text: 'd/dx (x³) = 3x²',                      color: '#ffffff', size: 22, accent: true, gap: true },
        { text: 'Step 2 — derivative of a linear term', color: 'rgba(200,232,255,0.5)', size: 12, mono: true, gap: true },
        { text: 'd/dx (4x) = 4',                        color: '#ffffff', size: 22, accent: true },
        { text: 'Result:  f\'(x) = 3x² + 4',            color: '#63c8ff', size: 16, italic: true, gap: true },
    ]
]

export const MODES = {
    Chalk: {
        board: '#2a4a1e', text: '#f0ead6', ui: '#f0ead6',
        root: '#1a1a1a', frame: '#5a3e1b',
        ruled: false, dusty: true,
    },
    Paper: {
        board: '#fdf6e3', text: '#1a1040', ui: '#1a1040',
        root: '#d8cfc0', frame: '#b8a888',
        ruled: true, dusty: false,
    },
    Neon: {
        board: '#04040f', text: '#00ffe7', ui: '#00ffe7',
        root: '#010108', frame: '#003344',
        ruled: false, dusty: false,
    },
    Gold: {
        board: '#08080f', text: '#c9a84c', ui: '#c9a84c',
        root: '#030307', frame: '#3a2808',
        ruled: false, dusty: false,
    },
}

export const PRESETS = [
    {
        category: 'Calculus',
        items: [
            { label: "Fundamental Theorem",  latex: "\\int_a^b f'(x)\\,dx = f(b) - f(a)" },
        ]
    },
    {
        category: 'Physics',
        items: [
            { label: "Gravitational Force",  latex: "F = G\\frac{m_1 m_2}{r^2}" },
    ]
    },
    {
        category: 'Engineering',
        items: [
            { label: "Convolution",          latex: "(f*g)(t) = \\int_{-\\infty}^{\\infty} f(\\tau)\\,g(t-\\tau)\\,d\\tau" },
        ]
    },
    {
        category: 'Statistics',
        items: [
            { label: "Normal Distribution",  latex: "f(x) = \\frac{1}{\\sigma\\sqrt{2\\pi}}\\,e^{-\\frac{(x-\\mu)^2}{2\\sigma^2}}" },
        ]
    },
]

// Speed → clip-reveal duration per line (ms).
export const SPEEDS = { 
    Slow: 9000, 
    Normal: 1200, 
    Fast: 500 
}

// Speed → server delay (seconds between SSE events)
export const SSE_DELAYS = { 
    Slow: 8.5, 
    Normal: 1.2, 
    Fast: 0.5 
}
