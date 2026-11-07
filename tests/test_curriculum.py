"""Keep the student's 2026–2027 semester sequence intact."""
from app.core import load_catalog


def test_calendar_sessions_match_provided_syllabus():
    data = load_catalog()
    assert len(data["subjects"]) == 1
    course = data["subjects"][0]
    assert course["id"] == "stom_prerest"
    assert course["total_sessions"] == 15
    assert len(course["lessons"]) == 15
    sessions = course["lessons"]
    assert [lesson["session_number"] for lesson in sessions] == list(range(1, 16))
    assert len({lesson["id"] for lesson in sessions}) == 15
    assert all(lesson["calendar_topic"] and lesson["focus"] for lesson in sessions)
    assert all(lesson["review_status"].startswith("DRAFT") for lesson in sessions)
    assert sum(len(lesson["questions"]) for lesson in sessions) == 145


def test_session_groups_and_legacy_ids():
    data = load_catalog()
    lessons = data["subjects"][0]["lessons"]
    assert lessons[0]["id"] == "ergonomika"
    assert lessons[2]["id"] == "qurilmalar"
    titles = [lesson["calendar_topic"] for lesson in lessons]
    assert titles[0] == titles[1]
    assert titles[2] == titles[3] == titles[4]
    assert titles[5] == titles[6]
    assert titles[7] == titles[8] == titles[9]
    assert titles[10] == titles[11]
    assert titles[12] == titles[13] == titles[14]
    assert len(set(titles)) == 6


def test_approved_public_sources_only():
    data = load_catalog()
    verified_links = {
        "https://e-library.sammu.uz/uz/book/4555",
        "https://e-library.sammu.uz/uz/book/5780",
        "https://e-library.sammu.uz/uz/book/2058",
        "https://e-library.sammu.uz/uz/book/3055",
        "https://e-library.sammu.uz/uz/book/343",
        "https://e-library.sammu.uz/uz/book/4516",
        "https://e-library.sammu.uz/uz/book/50",
    }
    for lesson in data["subjects"][0]["lessons"]:
        assert set(lesson["sources"]).issubset(verified_links)
        assert len(lesson["sources"]) >= 3
        assert len(lesson["sections"]) >= 3
        assert len(lesson["questions"]) >= 6
        assert all(len(question["options"]) == 4 for question in lesson["questions"])
