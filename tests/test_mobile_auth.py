"""Mobile approval regression coverage; no Telegram calls or real student accounts."""
import os
import tempfile
from pathlib import Path

os.environ["AUTO_SET_WEBHOOK"] = "0"
os.environ["AI_ENABLED"] = "0"

from fastapi.testclient import TestClient
from app import mobile_auth


def test_mobile_approval_gates_all_study_materials(monkeypatch):
    with tempfile.TemporaryDirectory() as temp:
        monkeypatch.setattr(mobile_auth, "DB_PATH", str(Path(temp) / "auth.db"))
        monkeypatch.setattr(mobile_auth, "_DB_READY", False)
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(mobile_auth.router)

        with TestClient(app) as client:
            payload = {"email": "student@example.org", "password": "a_secure_password_123!", "display_name": "Student"}
            bad_headers = {"Authorization": "Bearer not-a-valid-token"}
            assert client.get("/api/mobile/catalog").status_code == 401
            assert client.get("/api/mobile/diagrams/anat_1").status_code == 401
            assert client.get("/api/mobile/catalog", headers=bad_headers).status_code == 401
            assert client.post("/api/mobile/register", json=payload).status_code == 202
            assert client.post("/api/mobile/register", json=payload).status_code == 202
            assert len(mobile_auth.pending_accounts()) == 1
            account_id = mobile_auth.pending_accounts()[0]["id"]
            login = {"email": payload["email"], "password": payload["password"]}
            assert client.post("/api/mobile/login", json=login).status_code == 403
            assert client.post("/api/mobile/login", json={"email": payload["email"], "password": "incorrect"}).status_code == 401

            mobile_auth.set_account_status(account_id, "approved")
            approved = client.post("/api/mobile/login", json=login)
            assert approved.status_code == 200
            bearer = {"Authorization": "Bearer " + approved.json()["access_token"]}
            assert client.get("/api/mobile/me", headers=bearer).json()["email"] == payload["email"]
            catalog = client.get("/api/mobile/catalog", headers=bearer)
            assert catalog.status_code == 200
            assert catalog.headers["cache-control"] == "no-store"
            assert len(catalog.json()["subjects"]) == 6
            assert client.get("/api/mobile/diagrams/anat_1", headers=bearer).status_code == 200
            assert client.get("/api/mobile/diagrams/../../main.py", headers=bearer).status_code != 200

            mobile_auth.set_account_status(account_id, "revoked")
            assert mobile_auth.pending_accounts() == []
            assert client.get("/api/mobile/me", headers=bearer).status_code == 401
            assert client.get("/api/mobile/catalog", headers=bearer).status_code == 401
            assert client.get("/api/mobile/diagrams/anat_1", headers=bearer).status_code == 401
            assert client.post("/api/mobile/login", json=login).status_code == 403

            mobile_auth.set_account_status(account_id, "approved")
            again = client.post("/api/mobile/login", json=login)
            assert again.status_code == 200
            bearer = {"Authorization": "Bearer " + again.json()["access_token"]}
            assert client.post("/api/mobile/logout", headers=bearer).status_code == 200
            assert client.get("/api/mobile/catalog", headers=bearer).status_code == 401


def test_rejected_account_cannot_reapply_without_admin_action(monkeypatch):
    with tempfile.TemporaryDirectory() as temp:
        monkeypatch.setattr(mobile_auth, "DB_PATH", str(Path(temp) / "auth.db"))
        monkeypatch.setattr(mobile_auth, "_DB_READY", False)
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(mobile_auth.router)
        with TestClient(app) as client:
            payload = {"email": "student@example.org", "password": "a_secure_password_123!", "display_name": "Student"}
            assert client.post("/api/mobile/register", json=payload).status_code == 202
            account_id = mobile_auth.pending_accounts()[0]["id"]
            mobile_auth.set_account_status(account_id, "rejected")
            assert mobile_auth.pending_accounts() == []
            assert client.post("/api/mobile/register", json=payload).status_code == 202
            assert mobile_auth.pending_accounts() == []
            assert client.post("/api/mobile/login", json={"email":payload["email"],"password":payload["password"]}).status_code == 403
