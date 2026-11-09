"""Regression coverage for topic-specific anatomical illustration in the Mini App."""
from pathlib import Path
from fastapi.testclient import TestClient
from app import main


STATIC = Path(__file__).resolve().parents[1] / 'app' / 'static'


def test_anatomy_visual_menu_and_click_handler():
    js = (STATIC / 'app.js').read_text(encoding='utf-8')
    assert "anat_10:" in js
    assert 'VISUAL_LESSONS[l.id] ?' in js
    assert 'data-action="visual"' in js
    assert "case 'visual':if(state.lesson)showVisualLesson();break;" in js
    assert "function showVisualLesson()" in js
    assert 'Rasm orqali tushuntirish' in js


def test_illustration_asset_and_cache_bump():
    html = (STATIC / 'index.html').read_text(encoding='utf-8')
    assert '/static/app.js?v=1.0.4' in html
    assert '/static/style.css?v=1.0.4' in html
    svg = (STATIC / 'illustrations' / 'frontale-ethmoidale.svg').read_text(encoding='utf-8')
    assert svg.startswith('<svg')
    assert 'Os frontale' in svg
    assert 'Os ethmoidale' in svg
    assert 'Lamina perpendicularis' in svg
    response = TestClient(main.app).get('/static/illustrations/frontale-ethmoidale.svg')
    assert response.status_code == 200
    assert 'image/svg+xml' in response.headers.get('content-type', '')
