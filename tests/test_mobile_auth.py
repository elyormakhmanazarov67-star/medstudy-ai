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


def test_staging_admin_portal_requires_private_key(monkeypatch):
    from app import mobile_admin
    with tempfile.TemporaryDirectory() as temp:
        monkeypatch.setattr(mobile_auth, "DB_PATH", str(Path(temp) / "auth.db"))
        monkeypatch.setattr(mobile_auth, "_DB_READY", False)
        monkeypatch.setenv("MOBILE_ADMIN_PANEL_ENABLED", "1")
        monkeypatch.setenv("MOBILE_ADMIN_KEY", "A" * 40)
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(mobile_auth.router)
        app.include_router(mobile_admin.router)
        with TestClient(app) as client:
            assert client.get("/api/mobile/admin-console/pending").status_code == 403
            assert client.get("/api/mobile/admin-console/pending",
                              headers={"X-Mobile-Admin-Key": "incorrect"}).status_code == 403
            assert client.post("/api/mobile/admin-console/review",
                               json={"account_id": 1, "decision": "approved"}).status_code == 403
            assert client.get("/mobile-admin").status_code == 200
            registration_page = client.get("/mobile-register")
            assert registration_page.status_code == 200
            assert "Ro‘yxatdan o‘tish" in registration_page.text
            assert registration_page.headers["cache-control"] == "no-store"
            assert client.get("/api/mobile/catalog").status_code == 401
            payload = {"email": "new@example.org", "password": "secure-passphrase-123", "display_name": "Student"}
            assert client.post("/api/mobile/register", json=payload).status_code == 202
            headers = {"X-Mobile-Admin-Key": "A" * 40}
            pending = client.get("/api/mobile/admin-console/pending", headers=headers)
            assert pending.status_code == 200
            account_id = pending.json()["items"][0]["id"]
            assert client.post("/api/mobile/admin-console/review", headers=headers,
                               json={"account_id": account_id, "decision": "approved"}).status_code == 200
            assert client.post("/api/mobile/login",
                               json={"email": payload["email"], "password": payload["password"]}).status_code == 200
            assert client.post("/api/mobile/admin-console/review", headers=headers,
                               json={"account_id": account_id, "decision": "revoked"}).status_code == 200
        monkeypatch.setenv("MOBILE_ADMIN_PANEL_ENABLED", "0")
        with TestClient(app) as client:
            assert client.get("/mobile-admin").status_code == 404
            assert client.get("/api/mobile/admin-console/pending", headers={"X-Mobile-Admin-Key": "A" * 40}).status_code == 404



def test_admin_browser_remember_session_and_logout(monkeypatch):
    """A secure cookie replaces retyping the key; no password leaks to storage."""
    from fastapi import FastAPI
    from app import mobile_admin
    with tempfile.TemporaryDirectory() as temp:
        monkeypatch.setattr(mobile_auth, "DB_PATH", str(Path(temp) / "auth.db"))
        monkeypatch.setattr(mobile_auth, "_DB_READY", False)
        monkeypatch.setenv("MOBILE_ADMIN_PANEL_ENABLED", "1")
        monkeypatch.setenv("MOBILE_ADMIN_KEY", "test-secret-value-" + "B" * 40)
        app = FastAPI()
        app.include_router(mobile_auth.router)
        app.include_router(mobile_admin.router)
        with TestClient(app, base_url="https://testserver") as client:
            base = "/api/mobile/admin-console"
            assert client.get(base + "/session").status_code == 403
            assert client.get(base + "/pending").status_code == 403
            assert client.post(base + "/session", json={"remember": True},
                               headers={"X-Mobile-Admin-Key": "bad"}).status_code == 403
            result = client.post(
                base + "/session", json={"remember": True},
                headers={"X-Mobile-Admin-Key": "test-secret-value-" + "B" * 40},
            )
            assert result.status_code == 200
            cookie = result.headers["set-cookie"].lower()
            assert "httponly" in cookie
            assert "secure" in cookie
            assert "samesite=strict" in cookie
            assert "max-age=2592000" in cookie
            assert "path=/api/mobile/admin-console" in cookie
            assert client.get(base + "/session").json() == {"authenticated": True}
            assert client.get(base + "/pending").status_code == 200

            register = {
                "email": "cookie-test@example.org",
                "password": "long_password_for_testing",
                "display_name": "Cookie Tester",
            }
            assert client.post("/api/mobile/register", json=register).status_code == 202
            uid = mobile_auth.pending_accounts()[0]["id"]
            body = {"account_id": uid, "decision": "approved"}
            # Cookie-based state changes require a same-origin browser request.
            assert client.post(base + "/review", json=body).status_code == 403
            assert client.post(base + "/review", json=body,
                               headers={"Origin": "https://evil.example"}).status_code == 403
            assert client.post(base + "/review", json=body,
                               headers={"Origin": "https://testserver"}).status_code == 200

            assert client.post(base + "/logout",
                               headers={"Origin": "https://testserver"}).status_code == 200
            assert client.get(base + "/session").status_code == 403
            assert client.get(base + "/pending").status_code == 403


def test_admin_browser_cookie_invalid_after_key_rotation(monkeypatch):
    from fastapi import FastAPI
    from app import mobile_admin
    monkeypatch.setenv("MOBILE_ADMIN_PANEL_ENABLED", "1")
    monkeypatch.setenv("MOBILE_ADMIN_KEY", "C" * 40)
    app = FastAPI()
    app.include_router(mobile_admin.router)
    with TestClient(app, base_url="https://testserver") as client:
        base = "/api/mobile/admin-console"
        response = client.post(base + "/session", json={"remember": False},
                               headers={"X-Mobile-Admin-Key": "C" * 40})
        assert response.status_code == 200
        assert "max-age" not in response.headers["set-cookie"].lower()
        assert client.get(base + "/session").status_code == 200
        # Forged or expired session must not authenticate.
        client.cookies.clear()
        client.cookies.set(mobile_admin.SESSION_COOKIE, "v1.1.fake.invalid",
                           domain="testserver", path=mobile_admin.COOKIE_PATH)
        assert client.get(base + "/session").status_code == 403
        client.cookies.clear()
        assert client.post(base + "/session", json={"remember": True},
                           headers={"X-Mobile-Admin-Key": "C" * 40}).status_code == 200
        monkeypatch.setenv("MOBILE_ADMIN_KEY", "D" * 40)
        assert client.get(base + "/session").status_code == 403
