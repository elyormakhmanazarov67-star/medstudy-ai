"""Offline restore rehearsal of a SQLite snapshot; never touches live databases."""
from __future__ import annotations

import argparse
import sqlite3
import tempfile
from pathlib import Path


REQUIRED_TABLES = {"users", "attempts", "answers", "access_requests"}


def inspect(path: Path) -> None:
    uri = path.resolve().as_uri() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        result = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise ValueError("SQLite integrity check failed.")
        violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise ValueError("Database has invalid foreign-key references.")
        actual = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        if not REQUIRED_TABLES.issubset(actual):
            raise ValueError("This is not the expected MedStudy Mini App database.")
    finally:
        connection.close()


def rehearse(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError("Database snapshot file not found.")
    inspect(path)
    with tempfile.TemporaryDirectory(prefix="medstudy-restore-check-") as tempdir:
        restored = Path(tempdir) / "restored.sqlite"
        source = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        destination = sqlite3.connect(str(restored))
        try:
            source.backup(destination)
        finally:
            source.close()
            destination.close()
        inspect(restored)
    print("RESTORE_REHEARSAL_OK: schema, integrity and foreign-key checks passed.")
    print("No user details or database contents were printed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    args = parser.parse_args()
    rehearse(args.database)
