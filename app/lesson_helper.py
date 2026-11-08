"""Free, deterministic tutoring from the student's selected lesson.

No LLM, external API, conversation storage or paid credits. Answers quote
our original DRAFT material only; they must never be presented as AI-generated.
"""
from __future__ import annotations

from .tutor import _tokens

MODES = ("explain", "example", "recall", "oral")


def _ranked_sections(lesson: dict, question: str) -> list[tuple[int, int, dict]]:
    q = _tokens(question)
    result = []
    for i, section in enumerate(lesson.get("sections", [])):
        heading = str(section.get("heading", ""))
        body = str(section.get("body", ""))
        score = 5 * len(q & _tokens(heading)) + len(q & _tokens(body))
        result.append((score, i, section))
    return sorted(result, key=lambda it: (-it[0], it[1]))


def _ranked_quizzes(lesson: dict, question: str) -> list[tuple[int, int, dict]]:
    q = _tokens(question)
    result = []
    for i, item in enumerate(lesson.get("questions", [])):
        title = str(item.get("q", ""))
        explanation = str(item.get("explanation", ""))
        score = 3 * len(q & _tokens(title)) + len(q & _tokens(explanation))
        result.append((score, i, item))
    return sorted(result, key=lambda it: (-it[0], it[1]))


def prepare_answer(lesson: dict, question: str, mode: str = "explain") -> dict:
    """Return lesson excerpts or draft exercise, never inventing facts."""
    if mode not in MODES:
        raise ValueError("O‘rganish usuli noto‘g‘ri")
    question = question.strip()
    sections = _ranked_sections(lesson, question)
    quizzes = _ranked_quizzes(lesson, question)
    matches = [r for r in sections if r[0] > 0]
    if not matches:
        return {
            "answer": (
                "Bu savolga mos izoh tanlangan dars matnida topilmadi. "
                "Boshqa mavzuni tanlang yoki savolni darsdagi atamalar bilan qayta yozing. "
                "Hozircha bu yordamchi faqat dars matnidan izlaydi."
            ),
            "sections": [],
            "provider": "lesson",
            "notice": "Bepul konspekt yordamchisi. Sun’iy intellekt emas. Darslar mutaxassis tekshiruvidan o‘tmagan.",
        }
    _, _, section = matches[0]
    heading = str(section.get("heading", ""))
    body = str(section.get("body", "")).strip()
    if mode == "explain":
        answer = f"{heading}\n\n{body[:900]}"
    elif quizzes:
        item = quizzes[0][2]
        stem = str(item.get("q", ""))
        if mode == "example":
            correct = item.get("answer")
            options = item.get("options") or []
            if type(correct) is int and 0 <= correct < len(options):
                answer = (
                    f"Darsdagi misol:\n{stem}\n"
                    f"Javob: {options[correct]}\n"
                    f"Izoh: {item.get('explanation', '')}"
                )
            else:
                answer = f"{heading}\n\n{body[:900]}"
        else:
            variants = list(item.get("options", []))
            answer = (
                "O‘zingizni tekshiring:\n"
                + stem
                + ("\n" + "\n".join(f"{chr(65+i)}) {opt}" for i, opt in enumerate(variants)) if variants else "")
                + "\n\nBu bepul savol yordamchisi yozma javobni tekshira olmaydi. Javobni to‘liq testda tekshiring."
            )
    else:
        answer = f"{heading}\n\n{body[:900]}"
    return {
        "answer": answer[:1600],
        "sections": [heading],
        "provider": "lesson",
        "notice": "Bepul konspekt yordamchisi. Sun’iy intellekt emas. Klinik ko‘rsatma emas; materiallar DRAFT.",
    }
