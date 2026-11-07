from __future__ import annotations
import json
from pathlib import Path

CATALOG_FILE = Path(__file__).resolve().parent.parent / "content" / "lessons.json"


def load_catalog(path: Path = CATALOG_FILE) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    lesson_ids = set()
    for subject in data.get("subjects", []):
        for lesson in subject.get("lessons", []):
            assert lesson["id"] not in lesson_ids
            lesson_ids.add(lesson["id"])
            questions = lesson.get("questions", [])
            assert questions
            question_ids = set()
            for q in questions:
                assert q["id"] not in question_ids
                question_ids.add(q["id"])
                assert len(q["options"]) == 4
                assert type(q["answer"]) is int and 0 <= q["answer"] < 4
    assert data.get("subjects"), "Catalog is empty"
    return data


def find_lesson(data: dict, lesson_id: str):
    for subject in data["subjects"]:
        for lesson in subject["lessons"]:
            if lesson["id"] == lesson_id:
                return subject, lesson
    return None


def public_question(q: dict) -> dict:
    return {"id": q["id"], "q": q["q"], "options": q["options"]}


def grade(questions: list[dict], answers: list[int]):
    if len(answers) != len(questions):
        raise ValueError("Savollar soni mos emas")
    if any(type(a) is not int or not 0 <= a < 4 for a in answers):
        raise ValueError("Javob 0–3 oralig‘ida bo‘lishi kerak")
    details = [
        {
            "question_id": q["id"],
            "chosen": chosen,
            "answer": q["answer"],
            "correct": chosen == q["answer"],
            "explanation": q["explanation"],
        }
        for q, chosen in zip(questions, answers)
    ]
    return sum(x["correct"] for x in details), details
