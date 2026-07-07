from typing import Dict, List

RATING_LABELS: Dict[int, str] = {
    1: "Novice",
    2: "Familiar",
    3: "Confident",
    4: "Master",
}


def _format_prereq_block(prerequisites: Dict[str, int]) -> str:
    """
    Convert the rated prerequisites dict into a readable block for the course
    generation prompt. Appends a weak-areas line so the model deepens revision
    where the student scored 1–2.
    """
    if not prerequisites:
        return "  — No prerequisite ratings provided."

    lines: List[str] = []
    weak:  List[str] = []

    for key, val in prerequisites.items():
        clamped     = max(1, min(4, int(val)))
        human_label = key.replace("_", " ").title()
        rating_text = RATING_LABELS[clamped]
        lines.append(f"  - {human_label}: {rating_text} ({clamped}/4)")
        if clamped <= 2:
            weak.append(human_label)

    block = "\n".join(lines)
    if weak:
        block += f"\n  ⚠ Weak areas (give deeper revision): {', '.join(weak)}"
    return block