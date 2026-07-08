"""
Lumina Lesson Planning Engine
═══════════════════════════════════════════════════════════════════════════════
Purpose:
  Turns a lesson stub (title + key_concepts + prerequisite_revision +
  description) from the course plan into a fully structured lesson plan
  organised as: Lesson → Sections → Steps → Presentation Events.

  This engine handles PLANNING only.
  The downstream streaming_engine is responsible for real time streaming, timing, board
  animations, voice synthesis and learner-interrupt handling.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Architecture — four levels
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ┌──────────────────────────────────────────────────────────────────────┐
  │  LEVEL 1 — LESSON                                                    │
  │    What topic?  What learning objectives?  In what order?            │
  │    No speech or board actions here — only high-level intent.         │
  ├──────────────────────────────────────────────────────────────────────┤
  │  LEVEL 2 — SECTIONS                                                  │
  │    Natural classroom phases: Introduction, Prerequisite Review,      │
  │    Concept Introduction, Worked Example, Guided Practice,            │
  │    Independent Practice, Challenge, Summary.                         │
  │    Each section has a clear educational PURPOSE.                     │
  ├──────────────────────────────────────────────────────────────────────┤
  │  LEVEL 3 — STEPS                                                     │
  │    One atomic teaching action or idea per step.                      │
  │    Small enough that if a learner interrupts the teacher can         │
  │    resume from exactly this point without restarting the section.    │
  │    Every step carries a TEACHING OBJECTIVE — one sentence stating    │
  │    what the learner should grasp after this step completes.          │
  ├──────────────────────────────────────────────────────────────────────┤
  │  LEVEL 4 — PRESENTATION EVENTS                                       │
  │    The actual actions the AI teacher performs: SPEAK, WRITE,         │
  │    HIGHLIGHT, PAUSE, CIRCLE, UNDERLINE, ERASE, AWAIT_RESPONSE …      │
  │    Events carry a sync_with_previous flag that models concurrent     │
  │    classroom behaviour — writing on the board while talking.         │
  └──────────────────────────────────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Synchronisation model
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Every presentation event has a `sync_with_previous` boolean:

    false  →  start AFTER the previous event finishes  (sequential)
    true   →  start AT THE SAME TIME as the previous event  (concurrent)

  This models natural classroom behaviour.  A teacher does not finish
  speaking and then walk to the board.  They begin writing as they speak:

    { "type": "SPEAK",  "content": "Let me write this down…",  "sync_with_previous": false }
    { "type": "WRITE",  "content": "x^2 + 5x + 6 = 0",         "sync_with_previous": true  }
    { "type": "PAUSE",  "content": null,                         "sync_with_previous": false }

  Speech and board actions belong to the SAME teaching moment (the step),
  so synchronisation emerges naturally — there is no post-hoc alignment.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Section types  (in pedagogical sequence)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  INTRODUCTION          Continue from the external lesson-opener hook;
                        state objectives; connect to prior experience or
                        real-world relevance. Does not re-hook — see the
                        DO NOT WRITE YOUR OWN OPENING HOOK OR SECTION
                        TRANSITION rule.
  PREREQUISITE_REVIEW   Opens with a diagnostic check — pose the prior-
                        knowledge problem and ask what the learner would
                        do first (AWAIT_RESPONSE) — THEN reveal the full
                        worked review. Add one per weak prerequisite.
  CONCEPT_INTRODUCTION  Introduce the new concept formally: definition,
                        notation, and the key property to remember.
  WORKED_EXAMPLE        One fully-solved problem per section, every step
                        made explicit.  Must follow CONCEPT_INTRODUCTION.
  GUIDED_PRACTICE       Teacher and learner work through a problem together;
                        learner is prompted before each step is revealed.
  INDEPENDENT_PRACTICE  Learner attempts the problem; solution revealed after
                        an AWAIT_RESPONSE pause.
  CHALLENGE             Harder or exam-style extension problem.
  SUMMARY               Crystallise key results only; no new content.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Presentation event types
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  SPEAK           content = teacher's words (string, required)
  WRITE           content = KaTeX-renderable expression (string, required)
  HIGHLIGHT       content = target text already on the board (string, required)
  UNDERLINE       content = target text already on the board (string, required)
  CIRCLE          content = target text already on the board (string, required)
  ANNOTATE        content = annotation label or arrow description (string, required)
  ERASE           content = target expression or "all" (string, required)
  REVEAL          content = description of what is uncovered (string, required)
  PAUSE           content = null  (silent processing beat)
  AWAIT_RESPONSE  content = question posed to learner, or null

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEM-first rule  (non-negotiable)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Every CONCEPT_INTRODUCTION must be followed immediately by ≥ 2
  WORKED_EXAMPLE sections.  Every WORKED_EXAMPLE cluster must be
  followed by ≥ 1 practice section (GUIDED_PRACTICE or
  INDEPENDENT_PRACTICE).  Theory is never left without application.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Downstream wiring
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  POST /lesson/generate  →  calls generate_lesson()
  streaming_engine.py receives the lesson plan and adds timing,
  voice parameters, board animation keyframes, real time 
  lesson streaming and interrupt-resume state.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Schema returned by generate_lesson()
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{
  "lesson_id":           "ch1_l1",
  "lesson_title":        "Quadratic Equations by Factorisation",
  "subject":             "Mathematics",
  "grade_level":         "Grade 10",
  "goal":                "Ace Exams",
  "learning_objectives": ["string", ...],
  "key_concepts":        ["string", ...],
  "estimated_duration":  "55 min",
  "sections": [
    {
      "id":      "sec_intro",
      "type":    "INTRODUCTION | PREREQUISITE_REVIEW | CONCEPT_INTRODUCTION |
                  WORKED_EXAMPLE | GUIDED_PRACTICE | INDEPENDENT_PRACTICE |
                  CHALLENGE | SUMMARY",
      "title":   "string — human-readable section title",
      "purpose": "string — one sentence on the educational role of this section",
      "steps": [
        {
          "id":        "step_1",
          "objective": "string — what the learner should grasp after this step",
          "events": [
            {
              "type":               "SPEAK | WRITE | HIGHLIGHT | ...",
              "content":            "string | null",
              "sync_with_previous": false
            }
          ]
        }
      ]
    }
  ]
}

LaTeX convention for WRITE events:
  • Pure math:         "ax^2 + bx + c = 0"
  • Labelled step:     "\\text{Step 2:}\\quad (x+2)(x+3) = 0"
  • Board text:        "\\text{Zero-Product Property}"
  • Fraction:          "\\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}"
  All strings must be valid KaTeX input — no surrounding $…$ delimiters.
"""
import warnings
import re
from typing import Dict, List, Optional

from pipelines import llm_gateway as gateway
from prompts.lesson_plan_prompt import _LESSON_SYSTEM


# ─── Constants ────────────────────────────────────────────────────────────────
SECTION_TYPES: frozenset[str] = frozenset({
    "INTRODUCTION",
    "PREREQUISITE_REVIEW",
    "CONCEPT_INTRODUCTION",
    "WORKED_EXAMPLE",
    "GUIDED_PRACTICE",
    "INDEPENDENT_PRACTICE",
    "CHALLENGE",
    "SUMMARY",
})

EVENT_TYPES: frozenset[str] = frozenset({
    "SPEAK",
    "WRITE",
    "HIGHLIGHT",
    "UNDERLINE",
    "CIRCLE",
    "ANNOTATE",
    "ERASE",
    "REVEAL",
    "PAUSE",
    "AWAIT_RESPONSE",
})

# Section types that count as "practice" for STEM-first validation.
_PRACTICE_TYPES: frozenset[str] = frozenset({
    "GUIDED_PRACTICE",
    "INDEPENDENT_PRACTICE",
})

# ─── Prompt builder ───────────────────────────────────────────────────────────
def _build_lesson_prompt(
    lesson_id:             str,
    lesson_title:          str,
    key_concepts:          List[str],
    prerequisite_revision: str,
    description:           str,
    subject:               str,
    grade_level:           str,
    goal:                  str,
    weak_prerequisites:    List[str],
    source_context:        Optional[str],
) -> str:
    """
    Assembles the user message for the lesson generation call.
    All inputs come directly from the course plan lesson object.
    """
    weak_block = (
        "WEAK PREREQUISITE AREAS  (add one PREREQUISITE_REVIEW section for each):\n"
        + "\n".join(f"  • {w}" for w in weak_prerequisites)
        if weak_prerequisites
        else "  — No specific weak areas flagged."
    )

    prompt = (
        f"LESSON REQUEST\n"
        f"══════════════\n"
        f"Lesson ID    : {lesson_id}\n"
        f"Title        : {lesson_title}\n"
        f"Subject      : {subject}\n"
        f"Level        : {grade_level}\n"
        f"Goal         : {goal}\n\n"
        f"Key Concepts to teach:\n"
        + "\n".join(f"  {i+1}. {c}" for i, c in enumerate(key_concepts))
        + f"\n\nPrerequisite revision hint:\n  {prerequisite_revision}\n\n"
        f"Lesson description:\n  {description}\n\n"
        f"{weak_block}\n\n"
    )

    if source_context:
        # Inject a slice of the source material so worked examples can reference
        # problems directly from the learner's own textbook or notes.
        prompt += (
            f"SOURCE MATERIAL CONTEXT  (draw worked examples from this where relevant):\n"
            f"{source_context[:1200]}\n\n"
        )

    prompt += (
        "Now generate the complete structured lesson plan.\n\n"
        "Non-negotiable requirements:\n"
        "  1. Every CONCEPT_INTRODUCTION must be immediately followed by ≥ 1 WORKED_EXAMPLE sections.\n"
        "  2. Every WORKED_EXAMPLE cluster must be followed by ≥ 2 practice section\n"
        "     (GUIDED_PRACTICE or INDEPENDENT_PRACTICE).\n"
        "  3. Every step must have a clear, specific teaching objective.\n"
        "  4. SPEAK content must follow the TONE & DELIVERY rules above — vary\n"
        "     sentence rhythm, think out loud before revealing an answer, and\n"
        "     avoid the banned robotic openers list. Never robotic.\n"
        "  5. WRITE content must be valid KaTeX  (no $…$ delimiters).\n"
        "  6. Model concurrent speech + writing with sync_with_previous: true on the\n"
        "     WRITE event that follows a SPEAK event in the same teaching moment.\n"
        "  7. Insert a PAUSE after any substantial board writing.\n"
        "  8. Every WORKED_EXAMPLE section must end with a step that names the\n"
        "     most common mistake learners make at this type of problem.\n"
        "     use plain text/unicode symbols in the ANNOTATE content,\n "
        "     matching the mini-example format exactly — no LaTeX commands.\n"
        "  9. INDEPENDENT_PRACTICE sections must include an AWAIT_RESPONSE event\n"
        "     before the solution is revealed.\n"
        " 10. The first event in every step must have sync_with_previous: false.\n"
        " 11. WRITE-before-AWAIT_RESPONSE (critical): in GUIDED_PRACTICE and\n"
        "     INDEPENDENT_PRACTICE, always use WRITE events to put the problem\n"
        "     on the board BEFORE AWAIT_RESPONSE fires.  AWAIT_RESPONSE content\n"
        "     must be a short verbal question only — never the problem or an\n"
        "     equation.  Putting the problem in AWAIT_RESPONSE instead of WRITE\n"
        "     causes it to appear only in the panel, leaving the board blank.\n"
        " 12. PREREQUISITE_REVIEW OPENS WITH A DIAGNOSTIC CHECK (critical): these\n"
        "    sections MUST contain at least one WRITE event demonstrating a\n"
        "    concrete mathematical example — but they must NOT launch\n"
        "    straight into a teacher-led demonstration of it. A real teacher\n"
        "    revisiting last semester's work checks what the class still\n"
        "    remembers before re-explaining it. Model that: step_1 WRITEs a\n"
        "    title/label then the prerequisite problem (PROBLEM TITLE RULE),\n"
        "    states the task in a full sentence (rule 18), then fires\n"
        "    AWAIT_RESPONSE asking what the learner would do first — e.g.\n"
        "    'What's the first step here?' — BEFORE any part of the solution\n"
        "    is shown. Only step_2 onward reveals the worked review, with\n"
        "    further WRITE events, following the same rules as any other\n"
        "    reveal step: no predicted verdict (rule 21) and no duplicate\n"
        "    WRITEs of the same expression (rule 13).\n"
        "\n"
        "      ✗ BAD — jumps straight to the demonstration, never checks\n"
        "         what the learner already knows:\n"
        "        SPEAK 'Let's warm up. Watch this expansion closely.'\n"
        "        WRITE '(2x - 3)(x + 4)'\n"
        "        SPEAK 'We multiply each term in the first bracket by...'\n"
        "\n"
        "      ✓ GOOD — diagnostic first, exactly like a real classroom\n"
        "         revisiting prior material:\n"
        "        WRITE '\\text{Quick Check: Factorising}'\n"
        "        WRITE '2x^2 + 6x + 4'\n"
        "        SPEAK 'Before we move on, let's see what you remember —\n"
        "         how would you start factorising this?'\n"
        "        AWAIT_RESPONSE 'What's the first step here?'\n"
        "        [[ next step reveals the full worked solution ]]\n"
        "\n"
        "    See the PREREQUISITE_REVIEW mini-example above for the full\n"
        "    pattern end to end.\n"
        " 13. NEVER write the same expression twice in a row. In reveal steps "
        "    (PREREQUISITE_REVIEW step_2+, INDEPENDENT_PRACTICE, CHALLENGE, "
        "    GUIDED_PRACTICE step_2+), each "
        "    result is WRITEn ONCE. The closing SPEAK names the result verbally "
        "    only — do NOT follow it with another WRITE of identical content. "
        "    Duplicate WRITEs cause the board to stutter with the same "
        "    expression and make the lesson feel broken.\n"
        " 14. ONE WRITE = ONE MOVE (critical): never chain multiple '=' signs "
        "    in a single WRITE that represent different operations (e.g. "
        "    substituting a value AND evaluating the result in the same "
        "    line, like 'x + 5 = 2 + 5 = 7'). Split each transformation "
        "    into its own WRITE event so the board updates one step at "
        "    a time, matching the step-by-step granularity rules above.\n"
        " 15. Every CONCEPT_INTRODUCTION and every WORKED_EXAMPLE must include\n"
        "    at least one SPEAK event naming the likely wrong guess before\n"
        "    the correct answer is given (TONE & DELIVERY rule 3).\n"
        " 16. NO RE-HOOKING THE INTRODUCTION (critical): the very first SPEAK\n"
        "    event of the INTRODUCTION section must NOT try to catch attention\n"
        "    on its own — no dramatic scenario, bold claim, or rhetorical\n"
        "    question written purely to hook the learner. An external\n"
        "    lesson-opener already does that job live, immediately before\n"
        "    this section plays (see rule 7). This section's first SPEAK\n"
        "    should continue forward with something concrete — state what\n"
        "    will be achieved, connect to prior experience — not repeat the\n"
        "    opener's attention-grabbing move. It also must NOT be a flat\n"
        "    plan announcement like 'We're going to...' or 'Today we will...'\n"
        "    — see TONE & DELIVERY rules 6-7 for the full banned-opener list.\n"
        "17. FINAL ANSWER = SPOKEN, NOT WRITTEN AS A LABEL (critical): never put \n"
        "    the literal words 'final answer', 'solution', 'answer' in an ANNOTATE event. \n"
        "    Say them in the SPEAK line that reads the result aloud (e.g. 'So the final answer is...'),\n"
        "    and pair it with a synced WRITE event where 'content' is set to the exact mathematical expression\n"
        "    already on the board (e.g., 'x = 4'). See the FINAL-ANSWER RULE above.\n"
        " 18. CLEAR TASK BEFORE AWAIT_RESPONSE (critical): every AWAIT_RESPONSE\n"
        "    must be preceded by a SPEAK event, in the same or an earlier\n"
        "    event in that step, that states in a full sentence what the\n"
        "    learner is being asked to do — not just a bare fragment prompt.\n"
        "    A terse AWAIT_RESPONSE question with no framing SPEAK before it\n"
        "    (just 'here's a problem, go') leaves the learner unsure what's\n"
        "    being asked. Example: SPEAK 'Convert this equation\n"
        "    to slope-intercept form.' before WRITE-ing the problem and\n"
        "    firing AWAIT_RESPONSE with the short verbal question.\n"
        " 19. PROBLEM TITLE BEFORE EQUATION (critical): every PREREQUISITE_REVIEW,\n"
        "    GUIDED_PRACTICE, and INDEPENDENT_PRACTICE section must open its\n"
        "    board content with\n"
        "    a short \\text{...} title/label WRITE event, e.g. \\text{1. Solve\n"
        "    for } x  or  \\text{Find the Intersection Point} , BEFORE the\n"
        "    bare problem equation is WRITEn. This must be the very first WRITE\n"
        "    event in the section. A real teacher never opens a new problem by\n"
        "    silently writing a raw equation; they name the task first. See the\n"
        "    PROBLEM TITLE RULE and the PREREQUISITE_REVIEW / GUIDED_PRACTICE /\n"
        "    INDEPENDENT_PRACTICE mini-examples above for the exact pattern.\n"
        " 20. NO LITERAL '&' IN WRITE CONTENT (critical): KaTeX reserves '&' for\n"
        "    matrix/array/cases/align environments, which this schema never\n"
        "    uses. A bare '&' anywhere in WRITE content, including plain\n"
        "    \\text{...} labels written in ordinary English (e.g. '& Graphing'),\n"
        "    makes KaTeX throw a parse error and the board falls back to\n"
        "    showing raw, unrendered LaTeX source instead of typeset text.\n"
        "    Always spell it out as the word 'and' instead. See the WRITE\n"
        "    CONTENT CHARACTER RULE above.\n"
        " 21. REVEAL STEPS MUST NOT PREDICT THE VERDICT (critical): the SPEAK\n"
        "    event that opens the step immediately after any AWAIT_RESPONSE\n"
        "    (PREREQUISITE_REVIEW, GUIDED_PRACTICE, INDEPENDENT_PRACTICE, and\n"
        "    CHALLENGE alike) must\n"
        "    never contain a verdict word or phrase — 'Correct', 'Exactly',\n"
        "    'That's right', 'Not quite', 'Let's check that' — and must never\n"
        "    imply the learner's answer was right or wrong. A system outside\n"
        "    this engine grades the learner's actual typed answer and speaks\n"
        "    that acknowledgement live, in whatever tone the real grading\n"
        "    calls for; this script cannot know in advance what the learner\n"
        "    will type, so a guessed verdict here will contradict the real\n"
        "    one whenever the guess is wrong. Open these steps as a soft,\n"
        "    neutral continuation of the teaching action itself — e.g.\n"
        "    'Okay — now let's write the factorised form.' or drop straight\n"
        "    into the next action ('Setting each factor to zero gives us...').\n"
        "    See the PREREQUISITE_REVIEW, GUIDED_PRACTICE, and\n"
        "    INDEPENDENT_PRACTICE mini-examples above for the exact pattern.\n"
        " 22. NO SELF-WRITTEN HOOKS OR TRANSITIONS (critical): the first SPEAK\n"
        "    event of EVERY section — INTRODUCTION included — must NOT\n"
        "    contain its own attention-grabbing hook, transitional beat, or\n"
        "    re-framing sentence ('Alright,', 'Now let's...', 'Let's try one\n"
        "    together.', 'Your turn.', 'Okay, next up —', or a dramatic\n"
        "    scenario/question written purely to hook the learner). A\n"
        "    separate system outside this engine already speaks that live\n"
        "    immediately before this content plays — a lesson-opener before\n"
        "    INTRODUCTION, a one-sentence handshake before every other\n"
        "    section. A self-written hook or transition on top of that reads\n"
        "    as the same idea said twice in a row. Drop straight into the\n"
        "    concrete instructional content instead. See the DO NOT WRITE\n"
        "    YOUR OWN OPENING HOOK OR SECTION TRANSITION rule above for the\n"
        "    full explanation and examples.\n"
    )
    return prompt


# ─── Core generation function ─────────────────────────────────────────────────
async def generate_lesson(
    *,
    lesson_id:             str,
    lesson_title:          str,
    key_concepts:          List[str],
    prerequisite_revision: str,
    description:           str,
    subject:               str,
    grade_level:           str,
    goal:                  str,
    weak_prerequisites:    Optional[List[str]] = None,
    source_context:        Optional[str]       = None,
    model:                 Optional[str]       = "reasoning"
) -> Dict:
    """
    Generate a fully structured lesson plan.

    Called by POST /lesson/generate in routes.py.

    The returned lesson is hierarchically structured as:
        Lesson → Sections → Steps → Presentation Events

    This plan is passed downstream to streaming_engine.py, which does real time streaming
    adds timing, voice parameters, board animation keyframes, and interrupt-resume state.  
    This function handles planning only.

    Args:
        lesson_id:              e.g. "ch1_l2"
        lesson_title:           e.g. "Quadratic Equations by Factorisation"
        key_concepts:           List from the course plan lesson object
        prerequisite_revision:  String from the course plan lesson object
        description:            2–3 sentence description from the course plan
        subject:                e.g. "Mathematics"
        grade_level:            e.g. "Grade 12"
        goal:                   "Ace Exams" | "Deep Mastery" | "Build Project" |
                                "Pure Curiosity"
        weak_prerequisites:     Prerequisite labels rated ≤ 2 by the learner
        source_context:         Optional slice of source_summary from extracticting_engine.py
        model:                  Logical alias ("fast" / "default" / "reasoning")
                                or a literal vendor model id. Omit to use the
                                gateway's configured default — see
                                pipelines/llm_gateway.py for how that's set.

    Returns:
        Parsed lesson dict matching the schema in the module docstring.
        Pass to streaming_engine.stream_lesson() for delivery
        enrichment.

    Raises:
        RuntimeError          if the model response is truncated, or the
                              configured provider isn't set up (missing key)
        json.JSONDecodeError  if the model returns malformed JSON
        Exception             any other provider-level error propagates
    """
    prompt = _build_lesson_prompt(
        lesson_id             = lesson_id,
        lesson_title          = lesson_title,
        key_concepts          = key_concepts,
        prerequisite_revision = prerequisite_revision,
        description           = description,
        subject               = subject,
        grade_level           = grade_level,
        goal                  = goal,
        weak_prerequisites    = weak_prerequisites or [],
        source_context        = source_context,
    )

    try:
        print(f"CREATE COURSE MODEL: {model}")
        lesson = await gateway.complete_json(
            prompt,
            model       = model,
            system      = _LESSON_SYSTEM,
            max_tokens  = 16000,
            temperature = 0.3,
            reasoning_effort="medium",
        )
        
    except gateway.LLMGatewayError as exc:
        # Catch truncation before it becomes a cryptic JSON-parse error —
        # the gateway already detects this generically; here we just attach
        # lesson-specific guidance ("key_concepts" is the lever to pull).
        if "truncated" in str(exc).lower():
            raise RuntimeError(
                "Lesson plan was truncated (response exceeded max_tokens). "
                "Reduce the number of key_concepts or lesson scope and retry."
            ) from exc
        raise RuntimeError(str(exc)) from exc

    # Hard schema validation before any downstream processing.
    _validate_lesson_schema(lesson)

    # Pass 0 — enforce the ANNOTATE CONTENT RULE: reclassify any ANNOTATE
    # event that snuck in LaTeX/KaTeX content as a WRITE event instead, so
    # it renders on the board correctly rather than as raw escaped text.
    # Must run before the WRITE dedup passes so newly-converted WRITE
    # events are covered by them too.
    _convert_latex_annotations_to_writes(lesson)

    # Pass 0a — enforce the ANNOTATE PLACEMENT RULE: reclassify any
    # ANNOTATE event that still has a WRITE event coming later in the same
    # section as a WRITE event instead. ANNOTATE is a section-closing
    # aside only (e.g. a "Common mistake: ..." note after the final boxed
    # answer) — a caption sitting mid-derivation, before more board work
    # is still to come, has been observed to throw off the pacing of every
    # WRITE event that follows it on the board. Must run before the WRITE
    # dedup passes so newly-converted WRITE events are covered by them too.
    _enforce_annotate_placement_rule(lesson)

    # Pass 0b — KaTeX reserves "&" as the column-alignment separator for
    # matrix/array/cases/align environments, which this schema never uses.
    # A bare "&" in ANY WRITE content (including plain \text{...} labels)
    # makes KaTeX throw a parse error, and the frontend falls back to
    # showing the raw, unrendered LaTeX source on the board. Must run
    # after the ANNOTATE->WRITE passes (newly-converted content needs the
    # same fix) and before the dedup passes (so duplicate detection isn't
    # fooled by "&" vs. "and" spelling differences in otherwise-identical
    # content).
    _fix_ampersands_in_write_content(lesson)

    # Pass 1 — intra-step: drop back-to-back WRITE events with identical content.
    _deduplicate_consecutive_writes(lesson)

    # Pass 2 — cross-step: convert a WRITE to HIGHLIGHT when its content is
    # already visible on the board from an earlier step in the same section.
    # This eliminates repeated lines while keeping the teaching moment visible.
    _convert_duplicate_writes_to_highlights(lesson)

    # Soft STEM-first ratio check — warns but does not block the lesson.
    _warn_stem_ratio(lesson.get("sections", []))

    # Soft checks — warn but do not block the lesson.
    _warn_missing_hook_opener(lesson.get("sections", []))
    _warn_await_response_missing_task_framing(lesson.get("sections", []))

    return lesson


# ─── Schema validation ────────────────────────────────────────────────────────
_PROBLEM_TITLE_SECTION_TYPES: frozenset[str] = frozenset({
    "PREREQUISITE_REVIEW",
    "GUIDED_PRACTICE",
    "INDEPENDENT_PRACTICE",
})


def _check_write_before_await(section: Dict, sec_label: str) -> None:
    """
    For PREREQUISITE_REVIEW, GUIDED_PRACTICE, and INDEPENDENT_PRACTICE
    sections, verify that at least one WRITE event appears somewhere
    before the first AWAIT_RESPONSE across the section's steps.

    This guards against the board-blank bug: the model puts the problem into
    the AWAIT_RESPONSE content (which renders in the panel) instead of using a
    WRITE event (which renders on the board), leaving an empty slot on the board.

    Raises RuntimeError if a covered section has no WRITE before its first
    AWAIT_RESPONSE.
    """
    if section.get("type") not in _PROBLEM_TITLE_SECTION_TYPES:
        return

    seen_write       = False
    seen_await       = False

    for step in section.get("steps", []):
        for event in step.get("events", []):
            etype = event.get("type", "")
            if etype == "WRITE":
                seen_write = True
            if etype == "AWAIT_RESPONSE":
                seen_await = True
                if not seen_write:
                    raise RuntimeError(
                        f"Practice section '{sec_label}' (type: {section.get('type')}) "
                        f"has an AWAIT_RESPONSE event before any WRITE event. "
                        "The problem must be WRITEn on the board first; "
                        "AWAIT_RESPONSE content should be a short verbal question only. "
                        "This causes the problem to appear only in the panel, not the board. "
                        "Please retry."
                    )
                # After the first AWAIT_RESPONSE we reset the write guard so
                # each subsequent prompt in GUIDED_PRACTICE is also checked.
                seen_write = False


def _check_practice_problem_has_title(section: Dict, sec_label: str) -> None:
    """
    For PREREQUISITE_REVIEW, GUIDED_PRACTICE, and INDEPENDENT_PRACTICE
    sections, verify that the problem opens with a short board
    title/label BEFORE the bare equation is written — e.g.
    "\\text{1. Solve for } x" — mirroring how a real teacher opens a
    board problem by naming the task ("Solve for x", "Simplify the
    following equation") before writing the expression itself.

    Without this, the board jumps straight from one problem's boxed
    answer into the next problem's raw equation with no heading in
    between, so the learner has no visual cue that a new problem has
    started or what it's asking (this is the exact bug PROBLEM TITLE
    RULE in _LESSON_SYSTEM exists to fix).

    Heuristic: the FIRST WRITE event anywhere in the section must be a
    KaTeX text label (its content contains "\\text{"), not a bare
    mathematical expression. Every WRITE example in the prompt uses
    "\\text{...}" for labels and plain math for equations, so a first
    WRITE lacking "\\text{" means the model skipped the title.

    Raises RuntimeError if the section's first WRITE event has no
    "\\text{" label.
    """
    if section.get("type") not in _PROBLEM_TITLE_SECTION_TYPES:
        return

    for step in section.get("steps", []):
        for event in step.get("events", []):
            if event.get("type") != "WRITE":
                continue
            content = str(event.get("content") or "")
            if "\\text{" not in content:
                raise RuntimeError(
                    f"Practice section '{sec_label}' (type: "
                    f"{section.get('type')}) opens its board content with "
                    f"a bare equation ('{content}') and no problem title. "
                    "Real teachers write a short label first — e.g. "
                    "'\\text{1. Solve for } x' or "
                    "'\\text{Find the Intersection Point}' — before the "
                    "equation, so the learner knows a new problem has "
                    "started. Add a WRITE event with a \\text{...} label "
                    "as the FIRST WRITE event in this section, before any "
                    "bare equation. Please retry."
                )
            return  # only the section's first WRITE event is checked


# ANNOTATE CONTENT RULE (see _LESSON_SYSTEM) forbids LaTeX macros, braces/
# carets/underscores used as math syntax, and raw unicode math symbols in
# ANNOTATE content. This is the enforcement for that rule — the prompt
# alone doesn't stop the model from occasionally emitting genuine KaTeX
# (e.g. "\\sqrt{x^2}=x", "(2x)^2 - 9^2") inside an ANNOTATE event instead
# of a WRITE event. Matches: backslash-prefixed macros (\sqrt, \times,
# \rightarrow...), braces/carets/underscores (KaTeX grouping/sup/sub
# syntax), and the specific forbidden unicode symbols the prompt calls
# out (→ × ≠ ≤ ≥ ± ✓ ✗).
_ANNOTATE_LATEX_PATTERN = re.compile(r'\\[a-zA-Z]+|[\^_{}]|[→×≠≤≥±✓✗]')


def _convert_latex_annotations_to_writes(lesson: Dict) -> None:
    """
    Auto-repair pass: reclassify ANNOTATE events that violate the
    ANNOTATE CONTENT RULE (LaTeX/KaTeX content) as WRITE events instead.

    Why repair rather than hard-fail like _validate_lesson_schema does for
    empty WRITE content: this content isn't malformed or missing — it's
    usually genuine, useful board math (e.g. "\\sqrt{x^2}=x, \\sqrt{25}=5")
    that the model filed under the wrong event type. Per the engine's own
    WRITE vs. ANNOTATE rule, "introducing brand-new content" is WRITE's
    job, not ANNOTATE's — so reclassifying it is what the model should
    have done in the first place, not a fallback or a content mangle.

    Operates in-place on the lesson dict. Runs after _validate_lesson_schema
    (structure must be valid before we mutate it) and before the WRITE
    dedup passes below, so any newly-converted WRITE events are still
    subject to duplicate-detection against the rest of the section.
    """
    for section in lesson.get("sections", []):
        for step in section.get("steps", []):
            for event in step.get("events", []):
                if event.get("type") != "ANNOTATE":
                    continue
                content = str(event.get("content") or "")
                if _ANNOTATE_LATEX_PATTERN.search(content):
                    event["type"] = "WRITE"


# See the ANNOTATE PLACEMENT RULE in _LESSON_SYSTEM. ANNOTATE is meant to
# model a teacher's closing side-note after the board work for a section
# is already finished (e.g. "Common mistake: ..." after the final boxed
# answer) — never a caption planted mid-derivation. The prompt alone
# doesn't reliably stop the model from reaching for ANNOTATE right after
# explaining a fact it's about to use (e.g. naming an LCM before
# multiplying by it), even though a WRITE event for the next stage of the
# derivation is still coming later in the same section. This is the
# enforcement for that rule.
def _enforce_annotate_placement_rule(lesson: Dict) -> None:
    """
    Auto-repair pass: reclassify ANNOTATE events that occur before the
    last WRITE event in their section as WRITE events instead.

    Why repair rather than hard-fail like _validate_lesson_schema does:
    this content isn't malformed — it's genuine working content (e.g.
    "LCM of 3, 4, 6 is 12", "product = 6, sum = 5") that the model filed
    under the wrong event type. Per the engine's own WRITE vs. ANNOTATE
    rule, content the learner still needs while the derivation continues
    belongs on the board as a WRITE line, not floating in a caption — so
    reclassifying it is what the model should have done in the first
    place. Plain-language content (no existing "\\text{...}" wrapper) is
    wrapped in \\text{...} on conversion so it renders as a text line
    rather than being mis-parsed as KaTeX math.

    Operates in-place on the lesson dict. Runs after
    _convert_latex_annotations_to_writes (so an ANNOTATE already
    reclassified there for its LaTeX content is skipped here — it's no
    longer an ANNOTATE event) and before the WRITE dedup passes, so any
    newly-converted WRITE events are still subject to duplicate-detection
    against the rest of the section.
    """
    for section in lesson.get("sections", []):
        # Flatten to one ordered list of event dicts across all steps in
        # the section so "mid-section" is judged against the whole
        # section's board derivation, not just the current step.
        flat_events = [
            event
            for step in section.get("steps", [])
            for event in step.get("events", [])
        ]

        last_write_idx = None
        for idx, event in enumerate(flat_events):
            if event.get("type") == "WRITE":
                last_write_idx = idx

        if last_write_idx is None:
            continue  # no WRITE events in this section — nothing to enforce

        for idx, event in enumerate(flat_events):
            if event.get("type") != "ANNOTATE":
                continue
            if idx >= last_write_idx:
                continue  # trailing ANNOTATE — a legitimate closing aside

            content = str(event.get("content") or "").strip()
            if content and "\\text{" not in content:
                content = f"\\text{{{content}}}"
            event["content"] = content
            event["type"] = "WRITE"


# KaTeX reserves "&" as the column-alignment separator for matrix/array/
# cases/align environments — see https://katex.org/docs/supported.html.
# This schema never emits those environments, so a bare "&" anywhere in a
# WRITE event's content (most often inside a \text{...} label written in
# natural English, e.g. "\text{Forms & Graphing}") makes KaTeX throw
# "ParseError: Expected 'EOF', got '&'". When that happens, the frontend
# falls back to rendering the raw, unrendered LaTeX source string on the
# board instead of typeset text — this is the exact bug this pass fixes.
# Matches "&" with any surrounding whitespace so spacing comes out clean
# after substitution (" & " -> " and ", "&" -> " and ").
_WRITE_AMPERSAND_PATTERN = re.compile(r'\s*&\s*')


def _fix_ampersands_in_write_content(lesson: Dict) -> None:
    """
    Auto-repair pass: replace literal "&" characters in WRITE event content
    with the word "and".

    Why repair rather than hard-fail: "&" -> "and" is a safe, meaning-
    preserving substitution for the natural-English prose this schema
    puts inside \\text{...} labels, so there's no ambiguity to resolve
    with a retry — fixing it deterministically is strictly better than
    spending a retry asking the model to remember to escape or avoid it.

    Operates in-place on the lesson dict. Runs after
    _convert_latex_annotations_to_writes (so ANNOTATE content newly
    reclassified as WRITE is covered too) and before the WRITE dedup
    passes (so "&" vs. "and" spelling differences don't hide otherwise-
    identical duplicate content from those passes).
    """
    for section in lesson.get("sections", []):
        for step in section.get("steps", []):
            for event in step.get("events", []):
                if event.get("type") != "WRITE":
                    continue
                content = event.get("content")
                if content and "&" in str(content):
                    event["content"] = _WRITE_AMPERSAND_PATTERN.sub(
                        " and ", str(content)
                    ).strip()


def _warn_missing_hook_opener(sections: List[Dict]) -> None:
    """
    Soft validation: warns if the very first SPEAK event of the lesson
    (the first SPEAK in the INTRODUCTION section) opens with one of the
    banned plan-announcement prefixes.

    """
    banned_prefixes = (
        "we're going to", "we are going to", "today, we are going to",
        "today we are going to", "next, we'll", "next we'll", "so today",
        "we will", "this is", "now we just do the math", "let us now",
    )

    intro = next((s for s in sections if s.get("type") == "INTRODUCTION"), None)
    if not intro:
        return

    first_speak = next(
        (
            event.get("content", "") or ""
            for step in intro.get("steps", [])
            for event in step.get("events", [])
            if event.get("type") == "SPEAK"
        ),
        None,
    )
    if first_speak is None:
        return

    lowered = first_speak.strip().lower()
    if lowered.startswith(banned_prefixes):
        warnings.warn(
            "Plan-announcement violation: the lesson's first SPEAK event "
            f"opens with a banned plan-announcement phrase: {first_speak!r:.100}",
            stacklevel=2,
        )


def _warn_await_response_missing_task_framing(sections: List[Dict]) -> None:
    """
    Soft validation: warns if an AWAIT_RESPONSE event appears in a step with
    no SPEAK event before it (within the same step) that reads like a full
    sentence framing the task, rather than firing "cold" straight after a
    WRITE/PAUSE with no explanation of what's being asked.

    Heuristic only (word count + presence of a SPEAK at all) — this cannot
    perfectly judge "clarity", so it warns rather than blocks.
    """
    for section in sections:
        if section.get("type") not in _PRACTICE_TYPES:
            continue
        for step in section.get("steps", []):
            events = step.get("events", [])
            speak_before = ""
            for event in events:
                etype = event.get("type", "")
                if etype == "SPEAK":
                    speak_before = event.get("content", "") or ""
                elif etype == "AWAIT_RESPONSE":
                    word_count = len(speak_before.split())
                    if word_count < 4:
                        warnings.warn(
                            f"Task-framing violation: AWAIT_RESPONSE in step "
                            f"'{step.get('id')}' of section "
                            f"'{section.get('id') or section.get('title')}' has "
                            "no substantial SPEAK event before it explaining "
                            "what the learner is being asked to do.",
                            stacklevel=2,
                        )
                    speak_before = ""


def _deduplicate_consecutive_writes(lesson: Dict) -> None:
    """
    Remove WRITE events whose content is identical to the immediately preceding
    WRITE event within the same step (intra-step safety net).

    Handles the tight LLM pattern where the result is written and then
    immediately written again in the same step:

        WRITE  "10x + 2"      ← correct: result appears
        SPEAK  "So the answer is 10x + 2."
        WRITE  "10x + 2"      ← removed: identical, already on the board

    For cross-step duplicates (same expression written again in a later step
    of the same section), see _convert_duplicate_writes_to_highlights, which
    converts those to HIGHLIGHT events instead of silently dropping them.

    Operates in-place on the lesson dict.  Runs after _validate_lesson_schema
    so the structure is guaranteed to be valid before we mutate it.
    """
    for section in lesson.get("sections", []):
        for step in section.get("steps", []):
            events = step.get("events", [])
            last_write_content: Optional[str] = None
            filtered = []
            for event in events:
                if event.get("type") == "WRITE":
                    content = event.get("content", "")
                    if content == last_write_content:
                        # Identical back-to-back WRITE in the same step — drop it.
                        continue
                    last_write_content = content
                else:
                    # Non-WRITE event does not reset the dedup window —
                    # a SPEAK between two identical WRITEs is still a duplicate.
                    pass
                filtered.append(event)
            step["events"] = filtered


def _convert_duplicate_writes_to_highlights(lesson: Dict) -> None:
    """
    Cross-step deduplication: within each section, if a WRITE event's content
    matches something already written to the board in an earlier step, convert
    it to a HIGHLIGHT event rather than writing it again.

    Why HIGHLIGHT instead of drop?
    ───────────────────────────────
    Silently dropping a WRITE wastes the teaching moment.  If the teacher is
    returning to a formula they introduced two steps ago, the pedagogically
    correct action is to highlight the existing line — the learner's eye is
    drawn to it and the connection is reinforced without a jarring re-write.

    Scope: per section.  The board is conceptually cleared between sections
    (a new section typically starts with ERASE "all" or a fresh context),
    so content from a previous section does not count as "already on the board."

    ERASE awareness: if an ERASE "all" or ERASE targeting the specific content
    is encountered, the relevant content is removed from the board-state set so
    a subsequent WRITE of the same expression is treated as genuinely new.

    Operates in-place.  Must be called after _deduplicate_consecutive_writes
    so that intra-step duplicates are already removed before we scan cross-step.
    """
    for section in lesson.get("sections", []):
        board_content: set = set()   # expressions currently on the board

        for step in section.get("steps", []):
            events = step.get("events", [])

            for event in events:
                etype   = event.get("type", "")
                content = (event.get("content") or "").strip()

                if etype == "WRITE":
                    if content in board_content:
                        # Already visible on the board — highlight, don't re-write.
                        event["type"] = "HIGHLIGHT"
                    else:
                        board_content.add(content)

                elif etype == "ERASE":
                    if content.lower() == "all":
                        board_content.clear()
                    else:
                        # Targeted erase — remove just that expression if present.
                        board_content.discard(content)


def _check_prereq_has_write_and_diagnostic(section: Dict, sec_label: str) -> None:
    """
    For PREREQUISITE_REVIEW sections, verify that at least one WRITE event
    exists (prevents the model from lazily speaking about the prerequisite
    without examples on the board) AND that at least one AWAIT_RESPONSE
    event exists (prevents the model from skipping the diagnostic check
    and jumping straight into a teacher-led demonstration — see rule 12).
    """
    if section.get("type") != "PREREQUISITE_REVIEW":
        return

    has_write = any(
        event.get("type") == "WRITE"
        for step in section.get("steps", [])
        for event in step.get("events", [])
    )
    if not has_write:
        raise RuntimeError(
            f"Prerequisite review section '{sec_label}' is missing WRITE events. "
            "The AI must demonstrate the review with concrete math on the board, "
            "not just speak about it. Please retry."
        )

    has_await = any(
        event.get("type") == "AWAIT_RESPONSE"
        for step in section.get("steps", [])
        for event in step.get("events", [])
    )
    if not has_await:
        raise RuntimeError(
            f"Prerequisite review section '{sec_label}' is missing an "
            "AWAIT_RESPONSE event. Per rule 12, PREREQUISITE_REVIEW must open "
            "with a diagnostic check — pose the problem and ask the learner "
            "what they'd do first — BEFORE revealing the worked review. The "
            "AI skipped straight to a demonstration instead of checking prior "
            "knowledge first. Please retry."
        )


def _validate_lesson_schema(lesson: Dict) -> None:
    """
    Hard validation: raises RuntimeError if the model response does not meet
    the minimum structural requirements for the four-level hierarchy.

    Hierarchy validated:
        lesson  (dict)
          └─ sections  (list of dicts)
               └─ steps  (list of dicts)
                    └─ events  (list of dicts with 'type' and
                                'sync_with_previous')

    Why this is necessary:
        response_format={"type":"json_object"} guarantees a JSON object but
        does NOT enforce the internal schema.  The model can (and occasionally
        does) return "sections" as a string or list of strings.  Without this
        guard, _warn_stem_ratio and downstream engines crash with a cryptic
        AttributeError rather than a clear, actionable message.

    Raises:
        RuntimeError — with a message that identifies the exact level and
                       location of the structural violation.
    """
    if not isinstance(lesson, dict):
        raise RuntimeError(
            f"Lesson response is not a JSON object (got {type(lesson).__name__}). "
            "The model may have returned something unexpected — please retry."
        )

    # ── Level 2: sections ────────────────────────────────────────────────────
    if "sections" not in lesson:
        raise RuntimeError(
            "Lesson response is missing the 'sections' key. "
            "The model did not follow the required schema — please retry."
        )

    sections = lesson["sections"]
    if not isinstance(sections, list):
        raise RuntimeError(
            f"Lesson 'sections' must be a JSON array but got "
            f"{type(sections).__name__}. "
            "The model ignored the schema — please retry."
        )

    for sec_i, section in enumerate(sections):
        if not isinstance(section, dict):
            raise RuntimeError(
                f"Section {sec_i} must be a JSON object but got "
                f"{type(section).__name__} ({section!r:.80}). "
                "The model returned sections in the wrong format — please retry."
            )

        sec_label = section.get("id") or section.get("title") or str(sec_i)

        # ── Level 3: steps ───────────────────────────────────────────────────
        if "steps" not in section:
            raise RuntimeError(
                f"Section '{sec_label}' is missing the 'steps' key. "
                "The model did not follow the required schema — please retry."
            )

        steps = section["steps"]
        if not isinstance(steps, list):
            raise RuntimeError(
                f"Section '{sec_label}' — 'steps' must be a JSON array but got "
                f"{type(steps).__name__}. "
                "The model ignored the schema — please retry."
            )

        for step_i, step in enumerate(steps):
            if not isinstance(step, dict):
                raise RuntimeError(
                    f"Step {step_i} in section '{sec_label}' must be a JSON object "
                    f"but got {type(step).__name__}. "
                    "The model returned steps in the wrong format — please retry."
                )

            step_label = step.get("id") or str(step_i)

            # ── Level 4: events ──────────────────────────────────────────────
            if "events" not in step:
                raise RuntimeError(
                    f"Step '{step_label}' in section '{sec_label}' is missing "
                    f"the 'events' key. "
                    "The model did not follow the required schema — please retry."
                )

            events = step["events"]
            if not isinstance(events, list):
                raise RuntimeError(
                    f"Step '{step_label}' — 'events' must be a JSON array but got "
                    f"{type(events).__name__}. "
                    "The model ignored the schema — please retry."
                )

            for ev_i, event in enumerate(events):
                if not isinstance(event, dict):
                    raise RuntimeError(
                        f"Event {ev_i} in step '{step_label}', section '{sec_label}' "
                        f"must be a JSON object but got {type(event).__name__}. "
                        "Please retry."
                    )

                # Every event must have 'type' and 'sync_with_previous'.
                for required_key in ("type", "sync_with_previous"):
                    if required_key not in event:
                        raise RuntimeError(
                            f"Event {ev_i} in step '{step_label}', section "
                            f"'{sec_label}' is missing the '{required_key}' key. "
                            "The model did not follow the required schema — please retry."
                        )

                # WRITE events must carry actual content — a null WRITE renders
                # as a silent blank gap on the board (the most common symptom of
                # the "missing board content" bug).
                if event.get("type") == "WRITE":
                    write_content = event.get("content")
                    if not write_content or not str(write_content).strip():
                        raise RuntimeError(
                            f"WRITE event {ev_i} in step '{step_label}', section "
                            f"'{sec_label}' has null or empty content. "
                            "WRITE events must carry a non-empty KaTeX string — "
                            "use PAUSE (content=null) for silent beats, not WRITE."
                        )

                # Every event type except PAUSE and AWAIT_RESPONSE requires
                # non-empty 'content'. This is what catches a model that
                # invents fields like "action"/"target" instead of "content"
                # (e.g. {"type": "ANNOTATE", "action": "BOX", "target": ...})
                # — that shape has no 'content' key at all, and previously
                # slipped through validation only to render as a stray
                # literal word (like "BOX") on the board.
                _CONTENT_REQUIRED_TYPES = {
                    "SPEAK", "WRITE", "HIGHLIGHT", "UNDERLINE", "CIRCLE",
                    "ANNOTATE", "ERASE", "REVEAL",
                }
                ev_type = event.get("type")
                if ev_type in _CONTENT_REQUIRED_TYPES:
                    ev_content = event.get("content")
                    if not ev_content or not str(ev_content).strip():
                        raise RuntimeError(
                            f"{ev_type} event {ev_i} in step '{step_label}', "
                            f"section '{sec_label}' has null or empty "
                            f"'content'. Got keys: {sorted(event.keys())}. "
                            f"{ev_type} events must carry their payload in a "
                            "'content' string field — there is no 'action' "
                            "or 'target' field in this schema. The model "
                            "likely invented a nonstandard event shape — "
                            "please retry."
                        )

        # ── Practice sections: check WRITE appears before first AWAIT_RESPONSE ─
        _check_write_before_await(section, sec_label)

        # Practice sections: check the problem opens with a title/label WRITE
        _check_practice_problem_has_title(section, sec_label)

        # Prerequisite sections: check WRITE events exist AND a diagnostic
        # AWAIT_RESPONSE opens the section before the review is revealed
        _check_prereq_has_write_and_diagnostic(section, sec_label)


# ─── STEM-first soft validation ───────────────────────────────────────────────
def _warn_stem_ratio(sections: List[Dict]) -> None:
    """
    Soft validation: logs warnings when STEM-first structural rules are violated
    without blocking the lesson from being returned.

    Rules checked:
      Rule 1 — Every CONCEPT_INTRODUCTION must be immediately followed by
               ≥ 1 WORKED_EXAMPLE sections within the next 3 sections.

      Rule 2 — Every WORKED_EXAMPLE cluster (the last WORKED_EXAMPLE in a
               consecutive run) must be followed by ≥ 2 practice section
               (GUIDED_PRACTICE or INDEPENDENT_PRACTICE) within the next
               4 sections.

    Pre-condition:
      _validate_lesson_schema() must be called before this to guarantee
      that `sections` is a list of dicts.
    """
    section_types = [s.get("type", "") for s in sections]

    for i, stype in enumerate(section_types):

        # ── Rule 1: concept must be followed by ≥ 2 worked examples ─────────
        if stype == "CONCEPT_INTRODUCTION":
            window       = section_types[i + 1 : i + 4]
            worked_count = window.count("WORKED_EXAMPLE")
            if worked_count < 2:
                warnings.warn(
                    f"STEM-first violation [Rule 1]: CONCEPT_INTRODUCTION at "
                    f"index {i} ('{sections[i].get('title', '')}') is followed "
                    f"by only {worked_count} WORKED_EXAMPLE section(s) in the "
                    f"next 3 sections — required ≥ 2.  "
                    f"Following types: {window}",
                    stacklevel=2,
                )

        # ── Rule 2: last worked example in a run must precede practice ───────
        is_last_in_run = (
            stype == "WORKED_EXAMPLE"
            and (
                i + 1 >= len(section_types)
                or section_types[i + 1] != "WORKED_EXAMPLE"
            )
        )
        if is_last_in_run:
            window = section_types[i + 1 : i + 5]
            if not any(t in _PRACTICE_TYPES for t in window):
                warnings.warn(
                    f"STEM-first violation [Rule 2]: WORKED_EXAMPLE cluster "
                    f"ending at index {i} ('{sections[i].get('title', '')}') "
                    f"is not followed by a GUIDED_PRACTICE or "
                    f"INDEPENDENT_PRACTICE section within the next 4 sections.  "
                    f"Following types: {window}",
                    stacklevel=2,
                )