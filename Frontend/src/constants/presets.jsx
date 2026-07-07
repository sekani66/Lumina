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
