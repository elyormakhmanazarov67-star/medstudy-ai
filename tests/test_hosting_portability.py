"""Basic preflight checks for the future non-Railway, stateful VPS deployment."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent


def test_portable_hosting_is_safe_before_cutover():
    yaml = (ROOT / "hosting/compose.yaml").read_text(encoding="utf-8")
    env = (ROOT / "hosting/.env.example").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    caddy = (ROOT / "hosting/Caddyfile").read_text(encoding="utf-8")

    assert 'AUTO_SET_WEBHOOK: "0"' in yaml
    assert 'AI_ENABLED: "0"' in yaml
    assert 'DEV_PREVIEW: "0"' in yaml
    assert "DATABASE_PATH: /app/data/medstudy.db" in yaml
    assert "medstudy_data:/app/data" in yaml
    assert "api:8000" in caddy
    assert 'SITE_DOMAIN' in caddy
    assert 'COPY app ./app' in dockerfile
    assert 'COPY content ./content' in dockerfile
    assert 'AUTO_SET_WEBHOOK=0' in env
    assert "BOT_TOKEN=" in env
    assert "WEB_APP_URL=https://medstudy.example.org" in env
    assert "proxy:" in yaml and "api:" in yaml
    # TLS proxy only needs the public domain, never Telegram credentials.
    assert re.search(r'proxy:\n(?:(?!\nvolumes:).)*env_file: \.env', yaml, re.S) is None


def test_backup_is_consistent_and_private():
    backup = (ROOT / "hosting/backup.sh").read_text(encoding="utf-8")
    ignore = (ROOT / "hosting/.gitignore").read_text(encoding="utf-8")
    assert "original.backup(copy)" in backup
    assert "PRAGMA integrity_check" in backup
    assert "umask 077" in backup
    assert "docker compose exec -T api" in backup
    assert ".env" in ignore
    assert "backups/" in ignore
