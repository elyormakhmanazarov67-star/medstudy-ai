"""Free lesson helper never needs OpenAI, AI consent, or billable calls."""
from fastapi.testclient import TestClient
from app import main, tutor
from app.lesson_helper import prepare_answer
from app.store import Store
from tests.test_miniapp import TOKEN, UID, hdr


def test_free_helper_access_and_billing_off(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "BOT_TOKEN", TOKEN)
    monkeypatch.setattr(main, "ALLOWED_IDS", {UID})
    monkeypatch.setattr(main, "STORE", Store(str(tmp_path / "helper.sqlite")))
    monkeypatch.setenv("AI_ENABLED", "0")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = TestClient(main.app)
    body = {"lesson_id": "eng_l1", "question": "What is a tooth?", "mode": "explain"}
    assert client.post("/api/tutor/lesson", json=body).status_code == 401
    assert client.post("/api/tutor/lesson", json=body, headers=hdr()).status_code == 403
    assert client.post("/api/consent", headers=hdr()).status_code == 200
    response = client.post("/api/tutor/lesson", json=body, headers=hdr())
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "lesson"
    assert data["answer"]
    assert main.STORE.ai_usage(UID) == 0
    assert not main.STORE.has_ai_consent(UID)
    assert client.post("/api/tutor/ask", json=body, headers=hdr()).status_code == 503


def test_helper_modes_from_15_lesson_curriculum():
    lessons = main.CATALOG["subjects"][3]["lessons"]
    assert len(lessons) == 5
    for lesson in lessons:
        for mode in ("explain", "example", "recall", "oral"):
            result = prepare_answer(lesson, lesson["sections"][0]["heading"], mode)
            assert result["answer"]
            assert result["provider"] == "lesson"
            assert len(result["sections"]) <= 1


def test_helper_no_matching_topic_is_honest():
    lesson = main.CATALOG["subjects"][3]["lessons"][0]
    response = prepare_answer(lesson, "qwertyxyz zzzunknown", "explain")
    assert response["sections"] == []
    assert "topilmadi" in response["answer"]


def test_free_helper_rejects_invalid_and_preserves_privacy(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "BOT_TOKEN", TOKEN)
    monkeypatch.setattr(main, "ALLOWED_IDS", {UID})
    monkeypatch.setattr(main, "STORE", Store(str(tmp_path / "helper_2.sqlite")))
    client = TestClient(main.app)
    client.post("/api/consent", headers=hdr())
    assert client.post("/api/tutor/lesson", headers=hdr(), json={
        "lesson_id": "missing", "question": "What is a tooth?",
    }).status_code == 404
    assert client.post("/api/tutor/lesson", headers=hdr(), json={
        "lesson_id": "eng_l1", "question": "What is a tooth?", "mode": "unverified",
    }).status_code == 422
    assert client.post("/api/tutor/lesson", headers=hdr(), json={
        "lesson_id": "eng_l1", "question": "a",
    }).status_code == 422
    assert main.STORE.ai_usage(UID) == 0
