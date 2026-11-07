"""Private teacher-material uploads and downloads; no external services."""
import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from app import main, materials
from tests.test_miniapp import TOKEN, UID, hdr
from app.store import Store


def _test_client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'BOT_TOKEN', TOKEN)
    monkeypatch.setattr(main, 'ALLOWED_IDS', {UID})
    monkeypatch.setattr(main, 'STORE', Store(str(tmp_path / 'test.sqlite')))
    monkeypatch.setattr(main, 'MATERIALS_DIR', tmp_path / 'materials')
    monkeypatch.delenv('MATERIALS_ADMIN_IDS', raising=False)
    return TestClient(main.app)


def _bundle(name: str, data: bytes):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as z:
        z.writestr(name,data)
    return stream.getvalue()


def test_unavailable_and_authorized_file_download(tmp_path,monkeypatch):
    client=_test_client(tmp_path,monkeypatch)
    lesson=main.CATALOG['subjects'][3]['lessons'][0]
    file=lesson['teacher_materials'][0]['filename']
    key=materials.file_id(file)
    assert client.get('/api/materials/'+key).status_code==401
    assert client.post('/api/consent',headers=hdr()).status_code==200
    response=client.get('/api/lessons/eng_l1',headers=hdr()).json()
    assert response['teacher_materials'][0]['available'] is False
    assert client.get('/api/materials/'+key,headers=hdr()).status_code==404
    assert client.get('/api/materials/notvalid',headers=hdr()).status_code==404
    # Upload an authentic minimal PPTX-shaped Office ZIP (not an arbitrary .exe).
    presentation=_bundle('[Content_Types].xml',b'<Types/>')
    upload=client.post('/api/materials/upload/'+key,headers=hdr(),files={'file':(file,presentation,'application/vnd.openxmlformats-officedocument.presentationml.presentation')})
    assert upload.status_code==200,upload.text
    response=client.get('/api/lessons/eng_l1',headers=hdr()).json()
    assert response['teacher_materials'][0]['available'] is True
    downloaded=client.get('/api/materials/'+key,headers=hdr())
    assert downloaded.status_code==200
    assert downloaded.content==presentation
    assert 'no-store' in downloaded.headers['cache-control']


def test_bulk_upload_and_unknown_names_rejected(tmp_path,monkeypatch):
    client=_test_client(tmp_path,monkeypatch)
    client.post('/api/consent',headers=hdr())
    name='Calendar_plan-Preklinik restavratsion stomatologiya.pdf'
    good=_bundle(name,b'%PDF-1.4\nminimal test content')
    response=client.post('/api/materials/bundle',headers=hdr(),files={'archive':('teacher.zip',good,'application/zip')})
    assert response.status_code==200,response.text
    assert response.json()['uploaded']==1
    assert materials.stored_path(main.MATERIALS_DIR,name).is_file()
    bad=_bundle('../unapproved.txt',b'not allowed')
    response=client.post('/api/materials/bundle',headers=hdr(),files={'archive':('bad.zip',bad,'application/zip')})
    assert response.status_code==422
    assert not (tmp_path/'unapproved.txt').exists()


def test_upload_is_admin_only(tmp_path,monkeypatch):
    client=_test_client(tmp_path,monkeypatch)
    client.post('/api/consent',headers=hdr())
    monkeypatch.setenv('MATERIALS_ADMIN_IDS','123456789')
    name='Calendar_plan-Preklinik restavratsion stomatologiya.pdf'
    response=client.post('/api/materials/bundle',headers=hdr(),files={'archive':('teacher.zip',_bundle(name,b'%PDF-1.5\nfile'),'application/zip')})
    assert response.status_code==403
    assert client.get('/api/materials/admin',headers=hdr()).json()['is_admin'] is False
