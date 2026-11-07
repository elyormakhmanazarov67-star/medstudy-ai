"""Private, authenticated, persistent downloads of user-provided course files.

Only names listed in the teacher-material manifest are accepted; no public static mount.
Persistent Railway volume is mounted at /app/data in staging.
"""
from __future__ import annotations

import hashlib
import io
import os
import tempfile
import zipfile
from pathlib import Path

from fastapi import HTTPException

VALID_EXTS = {".pdf", ".pptx", ".docx", ".doc", ".ppt", ".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 75 * 1024 * 1024
MAX_UPLOAD_BYTES = 160 * 1024 * 1024
MAX_TOTAL_UNPACKED = 220 * 1024 * 1024


def manifest(catalog: dict) -> dict[str, str]:
    """Opaque public ids -> exact approved filenames from user-provided lessons."""
    result: dict[str, str] = {}
    for subject in catalog.get("subjects", []):
        for lesson in subject.get("lessons", []):
            for material in lesson.get("teacher_materials", []):
                filename = material.get("filename", "")
                if not filename or Path(filename).name != filename:
                    continue
                if Path(filename).suffix.lower() not in VALID_EXTS:
                    continue
                key = hashlib.sha256(filename.encode("utf-8")).hexdigest()[:24]
                if key in result and result[key] != filename:
                    raise RuntimeError("Material id collision")
                result[key] = filename
    return result


def file_id(filename: str) -> str:
    return hashlib.sha256(filename.encode("utf-8")).hexdigest()[:24]


def storage_dir(root: Path) -> Path:
    return Path(os.getenv("MATERIALS_DIR", str(root / "data" / "materials")))


def stored_path(directory: Path, filename: str) -> Path:
    # Original filenames are only used for downloads; disk names are opaque hashes.
    return directory / (file_id(filename) + Path(filename).suffix.lower())


def public_materials(items: list[dict], catalog: dict, directory: Path) -> list[dict]:
    known = manifest(catalog)
    result = []
    for item in items:
        info = dict(item)
        name = info.get("filename", "")
        key = file_id(name)
        path = stored_path(directory, name)
        if known.get(key) == name:
            info["file_id"] = key
            info["available"] = path.is_file()
            if path.is_file():
                info["size_bytes"] = path.stat().st_size
        else:
            info["available"] = False
        result.append(info)
    return result


def _save_stream(stream, filename: str, directory: Path, size_limit: int = MAX_FILE_SIZE) -> int:
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    destination = stored_path(directory, filename)
    fd, temporary = tempfile.mkstemp(prefix=".material-", dir=directory)
    size = 0
    try:
        with os.fdopen(fd, "wb") as out:
            while True:
                block = stream.read(1024 * 1024)
                if not block:
                    break
                size += len(block)
                if size > size_limit:
                    raise HTTPException(413, "Fayl juda katta")
                out.write(block)
        if not size:
            raise HTTPException(422, "Fayl bo‘sh")
        with open(temporary, "rb") as f:
            head = f.read(8)
        ext = Path(filename).suffix.lower()
        if ext == ".pdf" and not head.startswith(b"%PDF-"):
            raise HTTPException(422, "PDF formati noto‘g‘ri")
        if ext in {".docx", ".pptx"}:
            if not head.startswith(b"PK") or not zipfile.is_zipfile(temporary):
                raise HTTPException(422, "Office fayl formati noto‘g‘ri")
        if ext in {".doc", ".ppt"} and head != bytes.fromhex("D0CF11E0A1B11AE1"):
            raise HTTPException(422, "Eski Office fayl formati noto‘g‘ri")
        if ext in {".jpg", ".jpeg"} and not head.startswith(b"\xff\xd8\xff"):
            raise HTTPException(422, "JPEG formati noto‘g‘ri")
        if ext == ".png" and head != b"\x89PNG\r\n\x1a\n":
            raise HTTPException(422, "PNG formati noto‘g‘ri")
        os.chmod(temporary, 0o600)
        os.replace(temporary, destination)
        return size
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def save_upload(file, filename: str, catalog: dict, directory: Path) -> dict:
    permitted = manifest(catalog)
    if permitted.get(file_id(filename)) != filename:
        raise HTTPException(422, "Fayl o‘qituvchi materiallari ro‘yxatida topilmadi")
    count = _save_stream(file, filename, directory)
    return {"filename": filename, "size_bytes": count}


def import_bundle(stream, catalog: dict, directory: Path) -> list[dict]:
    known = set(manifest(catalog).values())
    stream.seek(0, io.SEEK_END)
    compressed_size = stream.tell()
    stream.seek(0)
    if compressed_size > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "ZIP fayl juda katta")
    if not zipfile.is_zipfile(stream):
        raise HTTPException(422, "Yaroqli ZIP fayl tanlang")
    results = []
    total = 0
    seen = set()
    with zipfile.ZipFile(stream) as archive:
        members = [x for x in archive.infolist() if not x.is_dir()]
        if len(members) > 40:
            raise HTTPException(413, "ZIP ichida fayllar juda ko‘p")
        for member in members:
            # Never extract paths supplied by the archive. Only approved basenames.
            filename = member.filename
            if filename not in known:
                raise HTTPException(422, "ZIP ichida ruxsat berilmagan fayl: " + filename[:100])
            if filename in seen:
                raise HTTPException(422, "ZIP ichida takrorlangan fayl bor")
            if member.file_size <= 0 or member.file_size > MAX_FILE_SIZE:
                raise HTTPException(413, "ZIP ichida juda katta yoki bo‘sh fayl bor")
            seen.add(filename)
            total += member.file_size
            if total > MAX_TOTAL_UNPACKED:
                raise HTTPException(413, "ZIP ochilganda juda katta hajm")
        for member in members:
            with archive.open(member, "r") as source:
                size = _save_stream(source, member.filename, directory)
            results.append({"filename": member.filename, "size_bytes": size})
    return results
