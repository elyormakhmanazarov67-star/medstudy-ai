"""v0.5 study plan: pure ranking + authenticated API."""
from fastapi.testclient import TestClient
from app import main
from app.study_plan import build_study_plan
from app.store import Store
from tests.test_miniapp import TOKEN, UID, hdr


def test_study_plan_priority_and_honest_labels():
    catalog = {
        "subjects": [
            {"id": "a", "title": "Fan A", "lessons": [
                {"id": "weak", "title": "Weak"},
                {"id": "new", "title": "New"},
                {"id": "high", "title": "High"},
                {"id": "retry", "title": "Retry"},
            ]}
        ]
    }
    latest = [
        {"lesson_id": "weak", "score": 2, "total": 10},
        {"lesson_id": "high", "score": 9, "total": 10},
        {"lesson_id": "retry", "score": 7, "total": 10},
    ]
    plan = build_study_plan(catalog, latest, {"retry": 2})
    assert plan["total_lessons"] == 4
    assert plan["attempted_lessons"] == 3
    assert plan["pending_lessons"] == 1
    assert plan["items"][0]["lesson_id"] == "weak"
    by_id = {p["lesson_id"]: p for p in plan["items"]}
    assert by_id["weak"]["status"] == "repeat"
    assert by_id["new"]["status"] == "new"
    assert by_id["high"]["status"] == "maintain"
    assert by_id["retry"]["status"] == "review_errors"
    assert by_id["new"]["last_full_percent"] is None


def test_study_plan_no_data():
    catalog = {"subjects":[{"id":"s","title":"S","lessons":[{"id":"l","title":"Lesson"}]}]}
    plan = build_study_plan(catalog, [], {})
    assert plan["items"][0]["status"] == "new"
    assert plan["pending_lessons"] == 1


def test_study_plan_requires_auth_and_consent(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "BOT_TOKEN", TOKEN)
    monkeypatch.setattr(main, "ALLOWED_IDS", {UID})
    monkeypatch.setattr(main, "STORE", Store(str(tmp_path / "isolated.sqlite")))
    client = TestClient(main.app)
    assert client.get("/api/study-plan").status_code == 401
    assert client.get("/api/study-plan", headers=hdr()).status_code == 403
    assert client.post("/api/consent", headers=hdr()).status_code == 200
    r = client.get("/api/study-plan", headers=hdr())
    assert r.status_code == 200
    assert r.json()["total_lessons"] == 2
    assert r.json()["attempted_lessons"] == 0
