"""Preklinik visual API: approved accounts only and one diagram per topic."""
import tempfile
from pathlib import Path
import json
import xml.etree.ElementTree as ET

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import mobile_auth


def test_all_preklinik_diagrams_are_access_scoped(monkeypatch):
    with tempfile.TemporaryDirectory() as temp:
        monkeypatch.setattr(mobile_auth, "DB_PATH", str(Path(temp) / "mobile-visuals.db"))
        monkeypatch.setattr(mobile_auth, "_DB_READY", False)
        mobile_auth.preklinik_visual_catalog.cache_clear()
        app = FastAPI()
        app.include_router(mobile_auth.router)
        with TestClient(app) as client:
            path = "/api/mobile/preklinik-visual/ergonomika"
            assert client.get(path).status_code == 401
            assert client.get(path, headers={"Authorization": "Bearer bad"}).status_code == 401

            register = {
                "email": "visual-student@example.org",
                "display_name": "Visual Student",
                "password": "very-safe-password-123",
            }
            assert client.post("/api/mobile/register", json=register).status_code == 202
            pending = mobile_auth.pending_accounts()
            assert len(pending) == 1
            account_id = pending[0]["id"]
            login = {"email": register["email"], "password": register["password"]}
            assert client.post("/api/mobile/login", json=login).status_code == 403

            mobile_auth.set_account_status(account_id, "approved")
            response = client.post("/api/mobile/login", json=login)
            assert response.status_code == 200
            headers = {"Authorization": "Bearer " + response.json()["access_token"]}

            catalog = mobile_auth.preklinik_visual_catalog()
            assert len(catalog) == 31
            for topic_id, expected in catalog.items():
                res = client.get("/api/mobile/preklinik-visual/" + topic_id, headers=headers)
                assert res.status_code == 200
                assert res.headers["cache-control"] == "no-store"
                data = res.json()
                assert data["title"] == expected["title"]
                assert data["facts"] == expected["facts"]
                assert len(data["facts"]) == 3
                doc = ET.fromstring(data["svg"])
                assert doc.tag == "{http://www.w3.org/2000/svg}svg"

            assert client.get("/api/mobile/preklinik-visual/no_such_lesson", headers=headers).status_code == 404
            assert client.get("/api/mobile/preklinik-visual/%2E%2E", headers=headers).status_code != 200
            mobile_auth.set_account_status(account_id, "revoked")
            assert client.get(path, headers=headers).status_code == 401
