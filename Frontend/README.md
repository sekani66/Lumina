# Math Annotator — Setup & Usage Guide

Real-time handwriting animation for mathematics, physics, and engineering equations.
Powered by **KaTeX** (LaTeX rendering) + **SVG stroke-dashoffset animation**.

---

## How It Works

1. You type or select a **LaTeX equation**
2. KaTeX renders it invisibly in the DOM — producing **mathematically perfect** SVG glyphs
3. The app extracts every SVG path (each stroke of every symbol)
4. It animates them one-by-one using `strokeDashoffset`, exactly like chalk on a board

This means **every symbol is perfect**: integrals, fractions, Greek letters, superscripts,
matrices, summations — anything LaTeX supports, the board can write.

---

## Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Node.js | 18 or higher | `node -v` |
| npm | 9 or higher | `npm -v` |

If you don't have Node.js: https://nodejs.org (download the LTS version)

---

## Installation

```bash
# 1. Navigate into the project folder
cd math-annotator

# 2. Install dependencies (~30 seconds)
npm install

# 3. Start the development server
npm run dev
```

Your browser will open automatically at **http://localhost:3000**

---

## Project Structure

```
math-annotator/
├── index.html                  # Entry HTML (loads KaTeX CSS from CDN)
├── vite.config.js              # Vite bundler config
├── package.json                # Dependencies
└── src/
    ├── main.jsx                # React root mount
    ├── App.jsx                 # Page router (Landing ↔ Board)
    ├── LandingPage.jsx         # Home screen with "Open the Board" button
    ├── BoardPage.jsx           # Chalkboard with animation controls
    ├── katexToAnimatedPaths.js # Core engine: LaTeX → SVG paths
    └── index.css               # Global styles
```

---

## Using the App

### Landing Page
- Click **"Open the Board"** to enter the chalkboard

### Board Page
**Left sidebar**
- **Custom LaTeX** — type any LaTeX expression, press `Ctrl+Enter` or click "Load equation"
- **Preset Equations** — click a category to expand, then click any equation name

**Board controls**
- **▶ Write** — animate the equation stroke by stroke
- **↺ Replay** — rerun the animation from scratch
- **Speed** — Slow / Normal / Fast
- **Mode** — Chalk / Paper / Neon / Gold (changes board appearance)

---

## LaTeX Quick Reference

| What you want | LaTeX syntax |
|--------------|-------------|
| x squared | `x^2` |
| x sub n | `x_n` |
| Fraction | `\frac{a}{b}` |
| Square root | `\sqrt{x}` |
| Integral | `\int_a^b f(x)\,dx` |
| Sum | `\sum_{i=0}^{n} i` |
| Greek alpha | `\alpha` |
| Greek pi | `\pi` |
| Partial derivative | `\partial` |
| Infinity | `\infty` |
| Vector (bold) | `\mathbf{v}` |
| Del / Nabla | `\nabla` |
| Times | `\times` |
| Approximately | `\approx` |
| Matrix | `\begin{pmatrix} a & b \\ c & d \end{pmatrix}` |

**Full KaTeX reference:** https://katex.org/docs/supported

---

## Example Equations to Try

```
# Einstein
E = mc^2

# Quadratic formula
x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}

# Euler's identity
e^{i\pi} + 1 = 0

# Gaussian integral
\int_{-\infty}^{\infty} e^{-x^2}\,dx = \sqrt{\pi}

# Maxwell's equations (Ampère)
\nabla \times \mathbf{B} = \mu_0 \mathbf{J} + \mu_0\varepsilon_0 \frac{\partial \mathbf{E}}{\partial t}

# Schrödinger equation
i\hbar\frac{\partial}{\partial t}\Psi(\mathbf{r},t) = \hat{H}\Psi(\mathbf{r},t)

# Matrix equation
A\mathbf{x} = \mathbf{b} \implies \mathbf{x} = A^{-1}\mathbf{b}

# Fourier transform
\hat{f}(\xi) = \int_{-\infty}^{\infty} f(x)\,e^{-2\pi i x\xi}\,dx

# Navier-Stokes
\rho\frac{D\mathbf{u}}{Dt} = -\nabla p + \mu\nabla^2\mathbf{u} + \mathbf{f}

# Taylor series
f(x) = \sum_{n=0}^{\infty} \frac{f^{(n)}(a)}{n!}(x-a)^n
```

---

## Build for Production

```bash
npm run build
# Output goes to ./dist — deploy this folder to any static host
```

---

## Troubleshooting

**"Could not render equation"**
- Check your LaTeX syntax. Common mistake: missing `\` before commands.
- Test your LaTeX at https://katex.org/#demo first.

**Board is blank after clicking Write**
- Make sure you clicked "Load equation" or selected a preset *before* pressing Write.

**Equation is too small / cut off**
- The board auto-scales to fit. Very long equations may appear small — break them into parts.

**Port 3000 already in use**
- Edit `vite.config.js` and change `port: 3000` to any free port (e.g. 3001).

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `react` + `react-dom` | UI framework |
| `katex` | LaTeX → HTML/SVG rendering |
| `vite` + `@vitejs/plugin-react` | Dev server & bundler |
