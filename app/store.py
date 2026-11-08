"""SQLite progress store: no names, messages or phone numbers kept."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

class Store:
    def __init__(self, path: str):
        self.path = str(Path(path).resolve())
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.init()

    def connect(self):
        conn = sqlite3.connect(self.path, timeout=15)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 15000")
        return conn

    def init(self):
        with self.connect() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
              user_id INTEGER PRIMARY KEY,
              consented_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS attempts (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
              lesson_id TEXT NOT NULL,
              score INTEGER NOT NULL,
              total INTEGER NOT NULL,
              mode TEXT NOT NULL DEFAULT 'full',
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS answers (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              attempt_id INTEGER NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
              question_id TEXT NOT NULL,
              chosen INTEGER NOT NULL,
              correct INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_attempt_user ON attempts(user_id, lesson_id, id);
            CREATE TABLE IF NOT EXISTS ai_consents (
                user_id INTEGER PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
                consented_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS ai_usage (
                user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                utc_day TEXT NOT NULL,
                requests INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, utc_day)
            );
            CREATE INDEX IF NOT EXISTS idx_ai_usage_day ON ai_usage(utc_day);
            """)
            cols = {r[1] for r in c.execute("PRAGMA table_info(attempts)")}
            if "mode" not in cols:
                c.execute("ALTER TABLE attempts ADD COLUMN mode TEXT NOT NULL DEFAULT 'full'")

    def has_consent(self, uid: int) -> bool:
        with self.connect() as c:
            return c.execute("SELECT 1 FROM users WHERE user_id=?", (uid,)).fetchone() is not None

    def consent(self, uid: int):
        with self.connect() as c:
            c.execute("INSERT OR IGNORE INTO users VALUES (?, ?)",
                (uid, datetime.now(timezone.utc).isoformat()))

    def delete_user(self, uid: int):
        with self.connect() as c:
            c.execute("DELETE FROM users WHERE user_id=?", (uid,))

    def save_attempt(self, uid: int, lid: str, score: int, details: list[dict], mode: str='full'):
        if mode not in ('full', 'retry', 'supplementary'):
            raise ValueError('Invalid attempt mode')
        if not self.has_consent(uid):
            raise PermissionError("Avval rozilik kerak")
        with self.connect() as c:
            cur = c.execute("INSERT INTO attempts(user_id, lesson_id, score, total, created_at, mode) VALUES (?, ?, ?, ?, ?, ?)",
                (uid,lid,score,len(details),datetime.now(timezone.utc).isoformat(),mode))
            c.executemany("INSERT INTO answers(attempt_id, question_id, chosen, correct) VALUES (?, ?, ?, ?)",
                [(cur.lastrowid,d["question_id"],d["chosen"],int(d["correct"])) for d in details])

    def latest(self, uid: int) -> list[dict]:
        with self.connect() as c:
            rows = c.execute("""SELECT a.lesson_id, a.score, a.total, a.created_at
                FROM attempts a
                JOIN (SELECT lesson_id, MAX(id) AS attempt_id FROM attempts WHERE user_id=? AND mode='full' GROUP BY lesson_id) x
                 ON x.attempt_id=a.id ORDER BY a.lesson_id""", (uid,)).fetchall()
            return [dict(lesson_id=r[0],score=r[1],total=r[2],created_at=r[3]) for r in rows]

    def latest_wrong_ids(self, uid: int, lesson_id: str) -> list[str]:
        with self.connect() as c:
            row = c.execute("SELECT id FROM attempts WHERE user_id=? AND lesson_id=? AND mode IN ('full', 'retry') ORDER BY id DESC LIMIT 1", (uid,lesson_id)).fetchone()
            if not row:
                return []
            return [r[0] for r in c.execute("SELECT question_id FROM answers WHERE attempt_id=? AND correct=0 ORDER BY id", (row[0],))]

    def attempt_history(self, uid: int, limit: int = 20) -> list[dict]:
        """Recent attempts, scoped to one user. No answer text is included."""
        limit = max(1, min(int(limit), 50))
        with self.connect() as c:
            rows = c.execute(
                """SELECT lesson_id, score, total, mode, created_at
                   FROM attempts WHERE user_id=?
                   ORDER BY id DESC LIMIT ?""", (uid, limit)
            ).fetchall()
            return [
                dict(lesson_id=r[0], score=r[1], total=r[2],
                     mode=r[3], created_at=r[4]) for r in rows
            ]

    def attempt_count(self, uid: int) -> int:
        with self.connect() as c:
            return c.execute("SELECT COUNT(1) FROM attempts WHERE user_id=?", (uid,)).fetchone()[0]


    def has_ai_consent(self, uid: int) -> bool:
        with self.connect() as c:
            return c.execute("SELECT 1 FROM ai_consents WHERE user_id=?", (uid,)).fetchone() is not None

    def consent_ai(self, uid: int) -> None:
        if not self.has_consent(uid):
            raise PermissionError('Avval ilova maxfiylik roziligi talab etiladi')
        with self.connect() as c:
            c.execute("INSERT OR IGNORE INTO ai_consents VALUES (?, ?)",
                      (uid, datetime.now(timezone.utc).isoformat()))

    def revoke_ai_consent(self, uid: int) -> None:
        with self.connect() as c:
            c.execute("DELETE FROM ai_consents WHERE user_id=?", (uid,))

    def ai_usage(self, uid: int) -> int:
        day = datetime.now(timezone.utc).date().isoformat()
        with self.connect() as c:
            row = c.execute('SELECT requests FROM ai_usage WHERE user_id=? AND utc_day=?', (uid,day)).fetchone()
            return row[0] if row else 0

    def ai_global_usage(self) -> int:
        """Return UTC-day total requests without returning any user information."""
        day = datetime.now(timezone.utc).date().isoformat()
        with self.connect() as c:
            return int(c.execute(
                'SELECT COALESCE(SUM(requests),0) FROM ai_usage WHERE utc_day=?',
                (day,)
            ).fetchone()[0])

    def reserve_ai_request(self, uid: int, per_user: int, global_limit: int) -> int:
        """Reserve one request atomically; no message content is stored.

        A reservation counts even if the upstream call later fails, preventing
        repeated failures and retries from bypassing the budget guard.
        """
        day = datetime.now(timezone.utc).date().isoformat()
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            if not c.execute('SELECT 1 FROM ai_consents WHERE user_id=?',(uid,)).fetchone():
                raise PermissionError('AI xizmati uchun alohida rozilik kerak')
            user_row = c.execute('SELECT requests FROM ai_usage WHERE user_id=? AND utc_day=?',(uid,day)).fetchone()
            used = user_row[0] if user_row else 0
            all_count = c.execute('SELECT COALESCE(SUM(requests), 0) FROM ai_usage WHERE utc_day=?',(day,)).fetchone()[0]
            if used >= per_user or all_count >= global_limit:
                raise ValueError('Kunlik AI so‘rovlar limiti tugadi')
            c.execute("INSERT INTO ai_usage(user_id, utc_day, requests) VALUES(?,?,1) "
                      "ON CONFLICT(user_id, utc_day) DO UPDATE SET requests = requests + 1", (uid,day))
        return used + 1
