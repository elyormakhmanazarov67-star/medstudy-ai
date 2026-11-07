"""Deterministic, privacy-preserving study suggestions.

No AI calls or personal attributes: only the latest full test per lesson
and the outstanding errors in the user's most recent attempt.
"""
from __future__ import annotations


def build_study_plan(catalog: dict, latest: list[dict], wrong_counts: dict[str, int]) -> dict:
    """Return a stable priority-ordered plan for a signed-in student's lessons."""
    by_lesson = {row["lesson_id"]: row for row in latest}
    items: list[dict] = []
    for subject in catalog["subjects"]:
        for lesson in subject["lessons"]:
            lid = lesson["id"]
            row = by_lesson.get(lid)
            missed = wrong_counts.get(lid, 0)
            score = None
            if row and row["total"] > 0:
                score = round(row["score"] * 100 / row["total"])
            if score is None:
                priority, status, action, why = (
                    1, "new", "Darsni boshlash",
                    "Bu mavzu bo‘yicha hali to‘liq test topshirilmagan."
                )
            elif score < 60:
                priority, status, action, why = (
                    0, "repeat", "Darsni qayta o‘qish",
                    "Oxirgi to‘liq test natijasi 60% dan kam."
                )
            elif missed:
                priority, status, action, why = (
                    1, "review_errors", "Xato savollarni takrorlash",
                    "Oxirgi mashqda hali xato savollar mavjud."
                )
            elif score < 80:
                priority, status, action, why = (
                    1, "practice", "Yana mashq qilish",
                    "Oxirgi to‘liq test natijasi 80% dan kam."
                )
            else:
                priority, status, action, why = (
                    2, "maintain", "Bilimni mustahkamlash",
                    "Oxirgi to‘liq test natijasi 80% yoki undan yuqori."
                )
            items.append({
                "lesson_id": lid, "lesson_title": lesson["title"],
                "subject_id": subject["id"], "subject_title": subject["title"],
                "last_full_percent": score, "wrong_count": missed,
                "status": status, "action": action, "reason": why,
                "_priority": priority,
            })
    items.sort(key=lambda x: x["_priority"])
    for item in items:
        item.pop("_priority")
    completed = sum(x["last_full_percent"] is not None for x in items)
    return {
        "total_lessons": len(items),
        "attempted_lessons": completed,
        "pending_lessons": len(items) - completed,
        "items": items,
        "disclaimer": "Tavsiyalar faqat test natijalariga asoslangan; tibbiy maslahat emas.",
    }
