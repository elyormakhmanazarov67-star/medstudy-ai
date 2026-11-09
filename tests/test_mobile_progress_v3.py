"""MedStudy AI 3.0 account-scoped progress sync tests."""
import tempfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import mobile_auth


def test_progress_is_protected_isolated_and_never_downgrades(monkeypatch):
    with tempfile.TemporaryDirectory() as temp:
        monkeypatch.setattr(mobile_auth, "DB_PATH", str(Path(temp) / "mobile-v3.db"))
        monkeypatch.setattr(mobile_auth, "_DB_READY", False)

        app = FastAPI()
        app.include_router(mobile_auth.router)
        with TestClient(app) as client:
            assert client.get("/api/mobile/progress").status_code == 401
            assert client.put("/api/mobile/progress", json={
                "lesson_id": "anat_1", "read": True, "best_score": 1,
            }).status_code == 401

            tokens = []
            ids = []
            for email in ("alpha@example.org", "beta@example.org"):
                payload = {
                    "email": email,
                    "display_name": "MedStudy Student",
                    "password": "long-safe-password-123",
                }
                assert client.post("/api/mobile/register", json=payload).status_code == 202
                account_id = mobile_auth.pending_accounts()[-1]["id"]
                ids.append(account_id)
                assert client.get("/api/mobile/progress").status_code == 401
                mobile_auth.set_account_status(account_id, "approved")
                response = client.post("/api/mobile/login", json={
                    "email": email, "password": payload["password"],
                })
                assert response.status_code == 200
                tokens.append({"Authorization": "Bearer " + response.json()["access_token"]})

            lesson_id = "anat_1"
            valid = {"lesson_id": lesson_id, "read": True, "best_score": 2}
            assert client.put("/api/mobile/progress", headers=tokens[0],
                              json=valid).status_code == 200

            response = client.get("/api/mobile/progress", headers=tokens[0])
            assert response.status_code == 200
            assert response.headers["cache-control"] == "no-store"
            assert response.json()["items"] == [
                {"lesson_id": lesson_id, "read": True, "best_score": 2},
            ]
            assert client.get("/api/mobile/progress", headers=tokens[1]).json() == {"items": []}

            downgraded = {"lesson_id": lesson_id, "read": False, "best_score": 1}
            response = client.put("/api/mobile/progress", headers=tokens[0], json=downgraded)
            assert response.status_code == 200
            assert response.json() == {"lesson_id": lesson_id, "read": True, "best_score": 2}

            # Unknown lesson IDs and impossible scores cannot poison the catalog.
            assert client.put("/api/mobile/progress", headers=tokens[0], json={
                "lesson_id": "made_up_topic", "read": True,
            }).status_code == 404
            assert client.put("/api/mobile/progress", headers=tokens[0], json={
                "lesson_id": lesson_id, "best_score": 9999,
            }).status_code == 422
            assert client.put("/api/mobile/progress", headers=tokens[0], json={
                "lesson_id": lesson_id, "read": False,
            }).status_code == 422

            mobile_auth.set_account_status(ids[0], "revoked")
            assert client.get("/api/mobile/progress", headers=tokens[0]).status_code == 401
            assert client.put("/api/mobile/progress", headers=tokens[0],
                              json=valid).status_code == 401
            assert client.get("/api/mobile/progress", headers=tokens[1]).status_code == 200
