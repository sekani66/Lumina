# Lumina – AI Interactive Teacher

> Lumina is a live AI teacher that transforms a learner's own material —
> textbook chapter, lecture notes, or study guide — into a structured,
> one-on-one lesson. Rather than waiting for students to ask questions, it
> teaches proactively: explaining concepts on a live whiteboard while
> narrating, checking understanding through in-lesson practice, identifying
> misconceptions as they form, and adapting its instruction before letting
> the learner move on.

---

## Overview

Students today are drowning in study material while starving for
understanding. Access to content has never been greater — endless videos,
courses, PDFs, AI chatbots, homework solvers — and yet millions of learners
still fail to master what they're taught. The bottleneck was never
availability. It's responsiveness.

Lumina embeds pedagogy directly into software instead of relying on a
bigger model or a cleverer prompt. It's a teaching engine that plans a
lesson, delivers it on a synchronized whiteboard + voice, checks
understanding at every step, and re-explains with a different pedagogical
approach when a learner is stuck — with the teaching logic living in code,
not just in an LLM's discretion.

---

## Documentation

A detailed description of the system architecture, teaching pipeline, AMD infrastructure, and design decisions can be found here:

[Lumina Documentation](docs/Lumina.pdf)

## Features

- PDF extraction into a structured lesson source (PyMuPDF span/heading/table analysis)
- Prerequisite-strength self-rating that personalizes the course plan
- AI-generated, pedagogically structured course + lesson plans
- Real-time SSE lesson streaming (board writes, highlights, pacing, narration)
- Streaming voice narration synced word-by-word to real generated audio
- Interactive whiteboard rendered with Konva (`react-konva`)
- Math notation rendered with KaTeX
- In-lesson Q&A with automatic escalation across seven teaching approaches
  (algebraic, analogy, numerical, contrast, backwards, story, visual)
- Confusion-point probing when repeated re-explanation isn't landing
- "Raised hand" interrupt flow that doesn't cut the teacher off mid-word
- Swappable LLM backend: OpenAI, Fireworks-hosted models, or a self-hosted
  vLLM instance on AMD Instinct GPUs — selected purely via `.env`, no code changes

---

## System Architecture

```
                Learning Material
        (Textbook • Notes • Curriculum • Topic)
                        │
                        ▼
            ┌────────────────────────┐
            │  PDF Extraction Engine │   PyMuPDF spans → headings →
            └────────────────────────┘   sections → key terms → LLM lesson gen
                        │
                        ▼
        (Prerequisite strength self-rating)
                        │
                        ▼
            ┌────────────────────────┐
            │  Course Creation Engine│   topic + goal (+ PDF source) → full
            └────────────────────────┘   personalised course plan
                        │
                        ▼
            ┌─────────────────────────┐
            │      Lesson Engine      │   Lesson → Sections → Steps →
            │ Lesson → Sections →     │   Presentation Events (SPEAK, WRITE,
            │ Steps → Presentation    │   HIGHLIGHT, UNDERLINE, CIRCLE,
            │ Events[SPEAK, WRITE,...]│   ANNOTATE, ERASE, REVEAL, PAUSE,
            └─────────────────────────┘   AWAIT_RESPONSE)
                        │
                        ▼
            ┌────────────────────────┐
            │    Streaming Engine    │   Server-Sent Events; concurrent
            │   (real-time SSE)      │◄─────────────────────────────────┐
            └────────────────────────┘                                  │
         ┌──────────────┴──────────────┐                                │
         ▼                             ▼                                │
    ┌─────────────────┐      ┌───────────────────────┐                  │
    │ Digital Board    │      │Voice Narration        │                 │
    │ (Konva, real-time│      │(OpenAI gpt-4o-mini-tts,│                │
    │  render)         │      │ audio clock drives     │                │
    │                  │      │ word-by-word reveal)   │                │
    └─────────────────┘      └───────────────────────┘                  │
            │                             │                             │
            └──────────────┬──────────────┘                             │
                           ▼                                            │
                        Student                                         │
                           │                                            │
                           ▼                                            │
                  ┌───────────────────┐                                 │
                  │   Answer Engine    │  ANSWER → ESCALATE → PROBE →   │
                  │ (Q&A lifecycle)    │  MICRO, understanding checks   │
                  └───────────────────┘◄────────────────────────────────┘
                            │
                            ▼
                  ┌────────────────────────┐
                  │      LLM Gateway       │  resolves "fast" / "default" /
                  │ (alias → provider)     │  "reasoning" aliases to a
                  └────────────────────────┘  concrete provider + model
                            │
            ┌───────────────┴─────────────────┐
            │                                 │
            ▼                                 ▼
      OpenAI / Fireworks API           Self-hosted vLLM (AMD Instinct)
```

The Answer Engine and Streaming Engine loop back into each other: a paused
lesson hands off to the Answer Engine for Q&A, and once understanding is
confirmed, control returns to the Streaming Engine to resume the lesson
with an LLM-generated bridge phrase rather than a jump cut.

---

## Technology Stack

### Frontend
- React 18 (function components, hooks)
- Vite
- `react-router-dom`
- `react-konva` / `konva` — whiteboard rendering
- KaTeX — math notation
- Plain CSS + JS style objects (no CSS framework)

### Backend
- Python, FastAPI, Uvicorn
- Server-Sent Events (SSE) for lesson/answer streaming
- PyMuPDF (`pymupdf`, imported as `fitz`) for PDF extraction
- `openai` SDK — talks to OpenAI directly and, via a custom base URL, to
  Fireworks-hosted and self-hosted vLLM models
- `python-dotenv` for environment loading

### AI
- Fast tier — self-hosted **Qwen3-14B** on vLLM (AMD Instinct GPU), used on
  every learner turn (answer grading, escalation decisions) where a few
  hundred milliseconds of latency matters
- Reasoning tier — **Qwen 3.7 Plus** on Fireworks AI's MI300X
  infrastructure, used for lesson planning and harder in-lesson
  explanations where extra "thinking" time is worth spending
- **gpt-4o-mini-tts** (OpenAI) — real-time streamed voice narration; the
  audio byte-stream itself drives word-reveal timing instead of a fixed
  per-word delay

### AMD Integration
- AMD Developer Cloud + AMD Instinct GPU
- vLLM inference server, ROCm
- Two-tier routing (fast / reasoning) lets the same codebase run entirely
  on AMD hardware, entirely on hosted APIs, or a mix of both — controlled
  by `LLM_FAST_MODEL` / `LLM_DEFAULT_MODEL` / `LLM_REASONING_MODEL` in `.env`

---

## Project Structure

```
Lumina/
├── Backend/
│   ├── api/
│   │   └── routes.py               # all HTTP + SSE endpoints
│   ├── config/
│   ├── models/
│   ├── pipelines/
│   │   ├── extracting_engine.py    # PDF → structured source
│   │   ├── lesson_engine.py        # lesson stub → board-ready lesson
│   │   ├── streaming_engine.py     # SSE delivery, pause/resume/hand-raise
│   │   ├── answer_engine.py        # Q&A lifecycle, escalation, probing
│   │   ├── voice_engine.py         # streamed TTS + word-timing
│   │   └── llm_gateway.py          # single seam to OpenAI/Fireworks/vLLM
│   ├── prompts/                    # system prompts per engine
│   ├── schemas/                    # Pydantic request/response models
│   ├── services/
│   │   └── assert_client.py        # guards against calling out with no LLM configured
│   ├── utils/
│   ├── main.py                     # FastAPI app + CORS
│   └── requirements.txt
│
├── Frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── sharedComponents.jsx
│   │   ├── constants/              # per-page constants (course/lesson/landing)
│   │   ├── pages/
│   │   │   ├── Default.jsx         # landing page
│   │   │   ├── SignIn.jsx / SignUp.jsx
│   │   │   ├── Home.jsx
│   │   │   ├── createCourse.jsx    # 3-step course creation flow
│   │   │   ├── Lesson.jsx          # board + voice streaming lesson player
│   │   │   └── SlidingExplainBoard.jsx
│   │   ├── styles/                 # CSS + JS style-object files
│   │   ├── utils/
│   │   │   ├── boardAnimations.jsx
│   │   │   ├── pcmAudioPlayer.jsx  # Web Audio playback of streamed PCM
│   │   │   ├── createCourseHelpers.jsx
│   │   │   ├── luminaThemes.jsx
│   │   │   └── signInHelper.jsx
│   │   ├── App.jsx                 # hash-based routing between pages
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   └── vite.config.js
│
├── requirements.txt
└── README.md
```

> **Note:** `Frontend/package.json` currently declares the package name
> `math-annotator` — a leftover from an earlier iteration of the project.
> Harmless, but worth renaming to `lumina-frontend` (or similar) for clarity.

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/sekani66/Lumina.git
cd Lumina
```

### 2. Install the backend

```bash
cd Backend
pip install -r requirements.txt
pip install python-dotenv   # required by llm_gateway.py; not yet in requirements.txt
```

### 3. Install the frontend

```bash
cd ../Frontend
npm install
```

### 4. Configure environment variables

**`Backend/.env`**

```env
OPENAI_API_KEY=sk-...
FIREWORKS_API_KEY=fw_...
# FIREWORKS_BASE_URL=https://api.fireworks.ai/inference/v1   # optional override

LLM_FAST_MODEL=Qwen/Qwen3-14B
LLM_DEFAULT_MODEL=accounts/fireworks/models/qwen3p7-plus
LLM_REASONING_MODEL=accounts/fireworks/models/qwen3p7-plus

VLLM_BASE_URL=http://<your-vllm-host>:8000/v1
VLLM_API_KEY=EMPTY
```

**`Frontend/.env`**

```env
VITE_API_BASE=http://localhost:8000
```
### 5. (Optional) Start a self-hosted AMD model server


```bash
/opt/venv/bin/python3.10 -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen3-14B \
  --host 0.0.0.0 \
  --port 8000
```

### 6. Start the backend

```bash
cd Backend
python -m uvicorn main:app --reload
```

### 7. Start the frontend

```bash
cd Frontend
npm run dev
```

---

## Usage

1. Open Lumina in your browser (`npm run dev` prints the local URL).
2. Sign in → Create Course.
3. Enter a topic and learning goal, and choose your source: upload a PDF or
   let Lumina generate a curriculum from scratch.
4. Rate your prerequisite strength on the fields Lumina surfaces, then
   submit to generate your personalised course plan.
5. Click a lesson to start it — the board and voice stream in together.
6. Use the hand-raise control below the board to ask a question mid-lesson
   without breaking the teacher's flow.

---

## API Overview

All routes are mounted under the FastAPI app in `Backend/main.py`; full
per-route documentation (request/response shapes, SSE event types) lives
in the docstring at the top of `Backend/api/routes.py`.

| Area | Endpoint | Purpose |
|---|---|---|
| Health | `GET /health` | Liveness probe; frontend falls back to local KaTeX-only rendering if this fails |
| Course creation | `POST /create/course/extract-pdf` | Run PDF extraction pipeline |
| | `POST /create/course/prerequisites` | Get prerequisite-rating fields for topic/goal (+ optional PDF source) |
| | `POST /create/course` | Generate the full personalised course plan |
| Lesson planning | `POST /lesson/generate` | Turn a lesson stub into a board-ready `teaching_script` |
| Streaming | `POST /stream/session/create` | Create a streaming session from a `teaching_script` |
| | `GET /stream/lesson` | Primary SSE lesson stream |
| | `POST /stream/pause` / `POST /stream/hand-raise` / `POST /stream/hand-lower` | Interrupt controls |
| | `GET /stream/resume` | Resume after Q&A with an LLM-generated bridge phrase |
| | `GET /stream/sessions`, `DELETE /stream/session/{id}`, `POST /stream/sessions/evict-stale` | Admin/session housekeeping |
| Answer engine | `POST /answer/ask` | Primary Q&A turn handler (answer / escalate / probe / micro) |
| | `POST /answer/understand` | Standalone understanding classification |
| | `POST /answer/escalate` | Re-explain with a new teaching approach |
| | `POST /answer/probe` | Locate a learner's exact confusion point |
| | `GET /stream/answer` | SSE replay of a stored answer envelope |

---

## Known Gaps / Follow-ups

- **`python-dotenv` is imported but not in `requirements.txt`** — add it, or
  `pip install` fails to surface the missing dependency until runtime.
- **No test suite** — no `pytest`/`vitest` setup for either side yet.
- **No database** — sign-in, course, and lesson-progress state have no
  persistence layer wired up yet; streaming sessions currently live in
  memory only (`Backend/pipelines/streaming_engine.py`) and are lost on
  restart.
- **No auth implementation** — `SignIn.jsx` / `SignUp.jsx` exist on the
  frontend, but there's no corresponding auth flow (JWT/session/OAuth) on
  the backend yet.
- **`Backend/config/` and `Backend/models/`** are present but currently
  empty — worth documenting their intended purpose or removing.
- **License** — none specified yet.

---