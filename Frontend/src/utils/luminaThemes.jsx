// src/utils/luminaTheme.js

const THEMES = {
  'COMMON ERROR': {
    labelColor: 'rgba(255,150,90,0.80)',
    borderColor: 'rgba(255,150,90,0.20)',
    bgColor: 'rgba(255,150,90,0.04)',
  },
  'WHY IT HAPPENS': {
    labelColor: 'rgba(255,210,80,0.80)',
    borderColor: 'rgba(255,210,80,0.20)',
    bgColor: 'rgba(255,210,80,0.04)',
  },
  'CORRECTION': {
    labelColor: 'rgba(90,220,130,0.80)',
    borderColor: 'rgba(90,220,130,0.20)',
    bgColor: 'rgba(90,220,130,0.04)',
  },
  'PRACTICE': {
    labelColor: 'rgba(185,120,255,0.80)',
    borderColor: 'rgba(185,120,255,0.20)',
    bgColor: 'rgba(185,120,255,0.04)',
  }
};

const DEFAULT_THEME = {
  labelColor: 'rgba(99,200,255,0.65)',
  borderColor: 'rgba(99,200,255,0.12)',
  bgColor: 'rgba(99,200,255,0.04)',
};

export const getLuminaTheme = (label) => {
  // Returns the matching theme, or defaults to the blue theme if not found
  return THEMES[label] || DEFAULT_THEME;
};


