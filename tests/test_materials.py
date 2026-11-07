"""Original source files cannot be uploaded or downloaded through the bot."""
from fastapi.testclient import TestClient
from app import main
from app.store import Store
from tests.test_miniapp import TOKEN, UID, hdr

def test_no_material_upload_or_download_endpoints(monkeypatch, tmp_path):
    monkeypatch.setattr(main, 'BOT_TOKEN', TOKEN)
    monkeypatch.setattr(main, 'ALLOWED_IDS', {UID})
    monkeypatch.setattr(main, 'DEV_PREVIEW', False)
    monkeypatch.setattr(main, 'STORE', Store(str(tmp_path / 'no_files.sqlite')))
    client = TestClient(main.app)
    assert not any(getattr(route, 'path', '').startswith('/api/materials') for route in main.app.routes)
    assert client.post('/api/consent', headers=hdr()).status_code == 200
    for path in ('/api/materials/admin', '/api/materials/1234567890abcdef12345678',
                 '/api/materials/bundle', '/api/materials/upload/1234567890abcdef12345678'):
        assert client.get(path, headers=hdr()).status_code in (404, 405)
        assert client.post(path, headers=hdr()).status_code in (404, 405)
    c=client.get('/api/catalog',headers=hdr())
    assert c.status_code==200
    assert all('teacher_material_count' not in l
               for s in c.json()['subjects'] for l in s['lessons'])
    for lid in ('ergonomika', 'eng_l1', 'latin_a1'):
        lesson=client.get('/api/lessons/'+lid,headers=hdr())
        assert lesson.status_code==200
        body=lesson.json()
        assert 'teacher_materials' not in body
        assert 'file_id' not in str(body)
        assert 'size_bytes' not in str(body)

def test_latin_curriculum_still_accessible_without_original_files(monkeypatch, tmp_path):
    monkeypatch.setattr(main, 'BOT_TOKEN', TOKEN)
    monkeypatch.setattr(main, 'ALLOWED_IDS', {UID})
    monkeypatch.setattr(main, 'STORE', Store(str(tmp_path / 'latin.sqlite')))
    client = TestClient(main.app)
    client.post('/api/consent',headers=hdr())
    first=client.get('/api/lessons/latin_a1',headers=hdr()).json()
    assert len(first['alphabet'])==25
    assert first['sections']
    assert first['questions']
    assert client.get('/api/health').json()['version']=='0.5.13-content-only'
