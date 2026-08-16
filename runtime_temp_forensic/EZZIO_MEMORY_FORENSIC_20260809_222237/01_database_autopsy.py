import sqlite3
from pathlib import Path

root = Path.cwd()
db = root / "runtime" / "memory" / "sqlite" / "cognitive_store.db"

print(f"ROOT={root}")
print(f"DB={db}")
print(f"DB_EXISTS={db.exists()}")

if not db.exists():
    raise SystemExit(20)

print(f"DB_SIZE={db.stat().st_size}")

conn = sqlite3.connect(str(db))
conn.row_factory = sqlite3.Row

print("\n[TABLES]")
tables = conn.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type='table'
    ORDER BY name
""").fetchall()

for row in tables:
    print(row["name"])

print("\n[SCHEMA memory_events]")
schema = conn.execute("""
    SELECT sql
    FROM sqlite_master
    WHERE type='table'
      AND name='memory_events'
""").fetchone()

print(schema["sql"] if schema else "MISSING")

if schema:
    print("\n[ROW COUNT]")
    count = conn.execute(
        "SELECT COUNT(*) AS n FROM memory_events"
    ).fetchone()["n"]

    print(f"COUNT={count}")

    print("\n[LAST 10 EVENTS]")
    rows = conn.execute("""
        SELECT
            event_id,
            event_type,
            trace_id,
            session_id,
            actor,
            timestamp,
            payload,
            consolidated
        FROM memory_events
        ORDER BY rowid DESC
        LIMIT 10
    """).fetchall()

    for row in rows:
        print(dict(row))

conn.close()
