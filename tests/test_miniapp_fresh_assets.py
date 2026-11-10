"""Regression tests for old Telegram WebView assets and missing Preklinik tab."""
from fastapi.testclient import TestClient
from app import main
from app import telegram_gateway


def test_mini_app_script_and_diagram_assets_cannot_be_stale():
    with TestClient(main.app) as client:
        page = client.get('/')
        assert page.status_code == 200
        assert 'app.js?v=1.0.7' in page.text
        assert 'no-store' in page.headers['cache-control']

        javascript = client.get('/static/app.js?v=1.0.7')
        assert javascript.status_code == 200
        assert 'no-store' in javascript.headers['cache-control']
        assert "l.subject_id==='stom_prerest'" in javascript.text
        assert 'data-action="preklinik-visual"' in javascript.text
        assert 'showPreklinikVisual' in javascript.text

        catalog = client.get('/static/illustrations/preklinik/catalog.json')
        assert catalog.status_code == 200
        assert 'no-store' in catalog.headers['cache-control']
        assert len(catalog.json()) == 31
        assert 'ergonomika' in catalog.json()

        diagram = client.get('/static/illustrations/preklinik/ergonomika.svg')
        assert diagram.status_code == 200
        assert 'no-store' in diagram.headers['cache-control']
        assert diagram.text.lstrip().startswith('<svg')


def test_versioned_telegram_entrypoint(monkeypatch):
    monkeypatch.setenv('WEB_APP_URL', 'https://medstudy.example.org')
    url = telegram_gateway.mini_app_launch_url()
    assert url.startswith('https://medstudy.example.org/?miniapp=preklinik-')
    assert 'telegram' not in url.lower()
