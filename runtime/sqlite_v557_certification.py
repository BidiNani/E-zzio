import os
import sys
import time
import threading
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path: sys.path.insert(0, ROOT)

MODULE_PATH = os.path.join(ROOT, "tools", "index_engine_v5_4.py")
spec = importlib.util.spec_from_file_location("sqlite_backend", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
SQLiteRepository = module.SQLiteRepository

class DummyLogger:
    def info(self, *a, **k): pass
    def error(self, *a, **k): pass

class DummyTelemetry:
    def add_db_stats(self, *a, **k): pass
    def inc_retry(self, *a, **k): pass

CONFIG = {
    "paths": {
        "db_path": os.path.join(ROOT, "runtime", "test_sqlite_v557.db"),
        "backup_dir": os.path.join(ROOT, "runtime", "backups")
    },
    "sqlite_pragmas": {
        "busy_timeout_ms": 30000,
        "journal_size_limit_bytes": 67108864,
        "mmap_size_bytes": 268435456
    },
    "retention": {"keep_max_backups": 5}
}

db = CONFIG["paths"]["db_path"]
if os.path.exists(db): os.remove(db)

repo = SQLiteRepository(CONFIG, DummyLogger(), DummyTelemetry())
repo.init_schema()  # Créera la table 'files' officielle avec ses 10 colonnes
print("[OK] Schéma officiel initialisé (table 'files')")

batch = []
for i in range(1000):
    batch.append((
        f"G:\\AI\\E-zzio\\file_{i}.py", f"file_{i}.py", "E-zzio", ".py",
        1.5, time.time(), 1000 + i, b"hash_blob_123"
    ))

repo.execute_write_batch(batch)

conn = repo.get_connection(read_only=True)
count = conn.execute("SELECT COUNT(*) FROM files WHERE is_deleted=0").fetchone()[0]
conn.close()
assert count == 1000
print("[OK] Batch 1000 écrit (Contrat officiel respecté)")

errors = []
def worker(offset):
    try:
        rows = [(f"G:\\AI\\E-zzio\\p_{offset+i}.py", f"p_{offset+i}.py", "E-zzio", ".py", 2.0, time.time(), 2000+offset+i, b"hash") for i in range(100)]
        repo.execute_write_batch(rows)
    except Exception as e:
        errors.append(repr(e))

threads = [threading.Thread(target=worker, args=(i * 1000,)) for i in range(10)]
for t in threads: t.start()
for t in threads: t.join()

assert not errors, errors
print("[OK] Concurrence 10 workers validée")

conn = repo.get_connection(read_only=True)
count = conn.execute("SELECT COUNT(*) FROM files WHERE is_deleted=0").fetchone()[0]
conn.close()

assert count == 2000
print(f"[OK] COUNT FINAL = {count}")

os.remove(db)
print("\nSQLITE_V557_CERTIFIED_10_10")
