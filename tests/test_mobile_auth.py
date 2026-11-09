"""Mobile auth regression coverage; no network or Telegram credentials."""
import os
import tempfile
from pathlib import Path

os.environ["AUTO_SET_WEBHOOK"] = "0"
os.environ["AI_ENABLED"] = "0"

from fastapi.testclient import TestClient
from app import mobile_auth


def test_mobile_auth_registration_approval_logout_and_revocation(monkeypatch):
    with tempfile.TemporaryDirectory() as temp:
        monkeypatch.setattr(mobile_auth, "DB_PATH", str(Path(temp) / "auth.db"))
        monkeypatch.setattr(mobile_auth, "_DB_READY", False)
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(mobile_auth.router)
        with TestClient(app) as client:
            payload = {"email": "student@example.org", "password": "a_secure_password_123!", "display_name": "Student"}
            response = client.post("/api/mobile/register", json=payload)
            assert response.status_code == 202
            assert client.post("/api/mobile/register", json=payload).status_code == 202
            assert client.post("/api/mobile/login", json={"email": payload["email"], "password": payload["password"]}).status_code == 403
            pending = mobile_auth.pending_accounts()
            assert len(pending) == 1
            mobile_auth.approve_account(pending[0]["id"], True)
            bad = client.post("/api/mobile/login", json={"email": payload["email"], "password": "incorrect"})
            assert bad.status_code == 401
            logged_in = client.post("/api/mobile/login", json={"email": payload["email"], "password": payload["password"]})
            assert logged_in.status_code == 200
            token = logged_in.json()["access_token"]
            headers = {"Authorization": "Bearer " + token}
            assert client.get("/api/mobile/me", headers=headers).json()["email"] == payload["email"]
            assert client.get("/api/mobile/me").status_code == 401
            assert client.post("/api/mobile/logout", headers=headers).status_code == 200
            assert client.get("/api/mobile/me", headers=headers).status_code == 401
            again = client.post("/api/mobile/login", json={"email": payload["email"], "password": payload["password"]})
            assert again.status_code == 200
            other = {"Authorization": "Bearer " + again.json()["access_token"]}
            mobile_auth.approve_account(pending[0]["id"], False)
            assert client.get("/api/mobile/me", headers=other).status_code == 401
