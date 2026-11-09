"""Anatomy picture explanations: no live API calls or patient images stored."""
from __future__ import annotations

import asyncio
import io

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import main, anatomy_vision, tutor
from app.store import Store
from tests.test_miniapp import TOKEN, UID, hdr


def sample_picture(fmt="JPEG", size=(256, 180)):
    image = Image.new("RGB", size, (240, 242, 230))
    out = io.BytesIO()
    image.save(out, format=fmt)
    return out.getvalue()


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "BOT_TOKEN", TOKEN)
    monkeypatch.setattr(main, "ALLOWED_IDS", {UID})
    monkeypatch.setattr(main, "DEV_PREVIEW", False)
    monkeypatch.setattr(main, "STORE", Store(str(tmp_path / "image-test.db")))
    monkeypatch.setenv("AI_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-test-key")
    monkeypatch.setenv("AI_DAILY_LIMIT", "2")
    monkeypatch.setenv("AI_GLOBAL_DAILY_LIMIT", "3")
    calls = []

    async def fake_explain(lesson, image_data_uri, question=""):
        calls.append((lesson["id"], image_data_uri, question))
        return {"answer": "Os frontale — kalla suyagining oldingi qismida."}

    monkeypatch.setattr(anatomy_vision, "explain_image", fake_explain)
    return TestClient(main.app), calls


def post_image(client, lesson_id="anat_10", picture=None, content_type="image/jpeg"):
    return client.post(
        "/api/anatomy/image-explain",
        headers=hdr(),
        data={"lesson_id": lesson_id, "question": "Lotincha nomini ayting"},
        files={"image": ("bone.jpg", picture if picture is not None else sample_picture(), content_type)},
    )


def test_normalization_rejects_invalid_or_oversized_file():
    with pytest.raises(ValueError):
        anatomy_vision.normalize_image(b"invalid", "image/jpeg")
    with pytest.raises(ValueError):
        anatomy_vision.normalize_image(sample_picture(), "image/gif")
    with pytest.raises(ValueError):
        anatomy_vision.normalize_image(b"a" * (anatomy_vision.MAX_IMAGE_BYTES+1), "image/jpeg")
    with pytest.raises(ValueError):
        anatomy_vision.normalize_image(sample_picture("PNG"), "image/jpeg")
    jpg = anatomy_vision.normalize_image(sample_picture(), "image/jpeg")
    assert jpg.startswith("data:image/jpeg;base64,")
    with pytest.raises(ValueError):
        anatomy_vision.normalize_image(sample_picture(size=(4100, 4100)), "image/jpeg")


def test_requires_login_access_and_separate_ai_consent(client):
    c, calls = client
    assert c.post("/api/anatomy/image-explain", data={"lesson_id": "anat_10"},
                  files={"image": ("bone.jpg", sample_picture(), "image/jpeg")}).status_code == 401
    assert post_image(c).status_code == 403  # privacy consent
    c.post("/api/consent", headers=hdr())
    assert post_image(c).status_code == 403  # separate OpenAI consent
    assert c.post("/api/tutor/consent", headers=hdr()).status_code == 200
    r = post_image(c)
    assert r.status_code == 200, r.text
    assert r.json()["remaining"] == 1
    assert calls[0][0] == "anat_10"
    assert calls[0][1].startswith("data:image/jpeg;base64,")
    assert "Os frontale" in r.json()["answer"]


def test_only_anatomy_and_real_supported_images(client):
    c, calls = client
    c.post("/api/consent", headers=hdr())
    c.post("/api/tutor/consent", headers=hdr())
    assert post_image(c, lesson_id="eng_l1").status_code == 403
    assert post_image(c, picture=b"not a jpeg").status_code == 422
    assert post_image(c, content_type="image/gif").status_code == 422
    assert post_image(c, picture=b"x" * (anatomy_vision.MAX_IMAGE_BYTES+1)).status_code == 422
    assert len(calls) == 0
    assert main.STORE.ai_usage(UID) == 0


def test_public_free_user_cannot_spend_ai_or_send_image(client, monkeypatch):
    from tests.test_miniapp import sign
    c, calls = client
    monkeypatch.setenv("PUBLIC_FREE_ENABLED", "1")
    outsider_headers=hdr(sign(uid=UID+700))
    c.post("/api/consent",headers=outsider_headers)
    r=c.post("/api/anatomy/image-explain", headers=outsider_headers,
       data={"lesson_id":"anat_10"},files={"image":("bone.jpg",sample_picture(),"image/jpeg")})
    assert r.status_code == 403
    assert not calls


def test_image_uses_shared_quota(client):
    c,calls = client
    c.post("/api/consent",headers=hdr())
    c.post("/api/tutor/consent",headers=hdr())
    assert post_image(c).status_code == 200
    assert post_image(c).status_code == 200
    assert post_image(c).status_code == 429
    assert len(calls)==2
    assert main.STORE.ai_usage(UID)==2


def test_openai_request_uses_stateless_image_input(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY","fake-test-key")
    recorded=[]
    original=httpx.AsyncClient

    def handler(req):
        data=__import__("json").loads(req.content)
        recorded.append(data)
        return httpx.Response(200,json={"status":"completed","output":[{
            "type":"message","content":[{"type":"output_text","text":"Os ethmoidale"}],
        }]})

    monkeypatch.setattr(anatomy_vision.httpx, "AsyncClient",
        lambda *a, **kw: original(*a,transport=httpx.MockTransport(handler),**kw))
    lesson=next(l for s in main.CATALOG["subjects"] for l in s["lessons"] if l["id"]=="anat_10")
    output=asyncio.run(anatomy_vision.explain_image(lesson,anatomy_vision.normalize_image(sample_picture(),"image/jpeg")))
    assert output["answer"]=="Os ethmoidale"
    req=recorded[0]
    assert req["store"] is False
    assert req["input"][0]["content"][1]["type"]=="input_image"
    assert "faqat anatomik lotin" in req["instructions"]
