-- Mirrors the original MedStudy Mini App SQLite schema. No existing
-- Railway accounts or quiz attempts are copied by applying this migration.
-- D1 enforces foreign keys automatically; do not toggle PRAGMA foreign_keys.
CREATE TABLE IF NOT EXISTS users (
  user_id INTEGER PRIMARY KEY, consented_at TEXT NOT NULL
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
  utc_day TEXT NOT NULL, requests INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id, utc_day)
);
CREATE INDEX IF NOT EXISTS idx_ai_usage_day ON ai_usage(utc_day);
CREATE TABLE IF NOT EXISTS access_requests (
  user_id INTEGER PRIMARY KEY,
  status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected', 'revoked')),
  requested_at TEXT NOT NULL,
  reviewed_at TEXT, reviewed_by INTEGER
);
CREATE INDEX IF NOT EXISTS idx_access_status ON access_requests(status, requested_at);
CREATE TABLE IF NOT EXISTS rate_limits (
  user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  action TEXT NOT NULL,
  window_utc_minute TEXT NOT NULL,
  requests INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id, action)
);
