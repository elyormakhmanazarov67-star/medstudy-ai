#!/usr/bin/env bash
# Consistent online SQLite backup, exported to the VPS host only.
set -euo pipefail
cd "$(dirname "$0")"
umask 077
mkdir -p backups
destination="backups/medstudy-$(date -u +%Y%m%d-%H%M%S).sqlite"
if ! docker compose exec -T api python -c '
import sqlite3, tempfile, shutil, os, sys
source = "/app/data/medstudy.db"
if not os.path.isfile(source):
    raise SystemExit("Database does not exist yet")
with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as item:
    filename = item.name
try:
    original = sqlite3.connect("file:" + source + "?mode=ro", uri=True)
    copy = sqlite3.connect(filename)
    try:
        original.backup(copy)
    finally:
        original.close()
        copy.close()
    with open(filename, "rb") as stream:
        shutil.copyfileobj(stream, sys.stdout.buffer)
finally:
    os.unlink(filename)
' > "$destination"; then
  rm -f "$destination"
  echo "SQLite backup failed" >&2
  exit 1
fi
python3 -c 'import sqlite3, sys; c=sqlite3.connect("file:"+sys.argv[1]+"?mode=ro",uri=True); result=c.execute("PRAGMA integrity_check").fetchone()[0]; c.close(); assert result=="ok", result' "$destination"
echo "Verified SQLite backup on host: $destination"
echo "Backups include student data. Copy an ENCRYPTED backup to another location."
