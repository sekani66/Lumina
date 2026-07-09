export const RATINGS = [
  { id: 1, label: 'Novice'    },
  { id: 2, label: 'Familiar'  },
  { id: 3, label: 'Confident' },
  { id: 4, label: 'Master'    },
]

export const TYPE_COLORS = {
  Fundamentals:   { bg: 'rgba(251,191,36,0.12)',  text: '#fbbf24' },
  'Core Concept': { bg: 'rgba(99,200,255,0.12)',  text: '#63c8ff' },
  Advanced:       { bg: 'rgba(167,139,250,0.12)', text: '#a78bfa' },
  Mastery:        { bg: 'rgba(52,211,153,0.12)',  text: '#34d399' },
  Review:         { bg: 'rgba(251,113,133,0.12)', text: '#fb7185' },
  Assessment:     { bg: 'rgba(251,146,60,0.12)',  text: '#fb923c' },
}

export const MAX_PDF_MB  = 30
export const MAX_PDF_BYTES = MAX_PDF_MB * 1024 * 1024
