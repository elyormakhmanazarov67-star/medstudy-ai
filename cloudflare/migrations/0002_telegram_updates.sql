-- Test Telegram webhook duplicate protection, no chat messages stored.
-- No Telegram webhook is enabled by creating this table.
CREATE TABLE IF NOT EXISTS telegram_updates (
  update_id INTEGER PRIMARY KEY,
  received_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_telegram_updates_time ON telegram_updates(received_at);
