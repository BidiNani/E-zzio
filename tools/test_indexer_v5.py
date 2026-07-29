import os
import unittest
import json
import sqlite3
import shutil
from tools.index_engine_v5 import WorkspaceIndexerV5, SQLiteRepository, setup_logger, TelemetryCollector

class TestWorkspaceIndexerV5(unittest.TestCase):
    def setUp(self):
        self.test_dir = r"G:\AI\E-zzio\data\test_env"
        os.makedirs(self.test_dir, exist_ok=True)
        
        self.config = {
            "paths": {
                "root_scan": [self.test_dir],
                "db_path": os.path.join(self.test_dir, "test_index.db"),
                "backup_dir": os.path.join(self.test_dir, "backups"),
                "log_path": os.path.join(self.test_dir, "test.log")
            },
            "performance": {"num_hash_workers": 2, "batch_size": 10, "queue_max_size": 100, "use_blake3_if_available": False},
            "sqlite_pragmas": {"busy_timeout_ms": 5000, "journal_size_limit_bytes": 10485760, "mmap_size_bytes": 10485760, "page_size": 4096},
            "retention": {"keep_max_backups": 2, "full_integrity_check_interval_days": 7},
            "exclusions": {"dirs": [".git"], "extensions": [".py", ".txt"]}
        }
        
        # Fichiers de simulation
        with open(os.path.join(self.test_dir, "script1.py"), "w") as f: f.write("print('Hello World')")
        with open(os.path.join(self.test_dir, "doc1.txt"), "w") as f: f.write("Documentation test")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_full_index_flow(self):
        logger = setup_logger(self.config["paths"]["log_path"])
        telemetry = TelemetryCollector()
        repo = SQLiteRepository(self.config, logger, telemetry)
        repo.init_schema()
        
        # Test d'insertion
        conn = repo.get_connection()
        res = conn.execute("PRAGMA quick_check;").fetchone()
        self.assertEqual(res[0], "ok")
        conn.close()

if __name__ == "__main__":
    unittest.main()
