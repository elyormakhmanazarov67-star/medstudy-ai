"""Test the offline restoration tool using a synthetic, zero-secret database."""
from pathlib import Path
import sqlite3
import pytest

from app.store import Store
from hosting.verify_restore import rehearse


def test_rehearsal_with_valid_snapshot(tmp_path):
    path = tmp_path / "fake-students.sqlite"
    store = Store(str(path))
    store.consent(900000001)
    rehearse(path)


def test_rehearsal_rejects_foreign_database(tmp_path):
    path = tmp_path / "other.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE unrelated (x INTEGER)")
    with pytest.raises(ValueError, match="MedStudy"):
        rehearse(path)


def test_rehearsal_refuses_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        rehearse(tmp_path / "missing.sqlite")
