import unittest
import os
import tempfile
import shutil
import sqlite3
import time
from runtime.telemetry.storage import TelemetryStorage
from runtime.telemetry.health import HealthMonitor
from runtime.telemetry.collector import TelemetryCollector
from runtime.telemetry.metrics import ExecutionMetric

class TestTelemetryHardening(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_hardened.db")
        self.storage = TelemetryStorage(db_path=self.db_path, retention_days=1)
        
        # Injection propre (sans singleton fragile)
        self.collector = TelemetryCollector(storage=self.storage, batch_size=2)
        self.collector.start()

    def tearDown(self):
        self.collector.stop() # Assure le vidage asynchrone et ferme la base
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_async_batch_and_composite_health(self):
        self.collector.record_execution(ExecutionMetric("ex_1", "action_a", "SUCCESS", 100.0, 1.0, "LOW"))
        self.collector.record_execution(ExecutionMetric("ex_2", "action_b", "FAILED", 600.0, 1.0, "HIGH", category="TIMEOUT"))
        
        # Laisse le temps au writer thread de dépiler
        time.sleep(0.5)
        
        monitor = HealthMonitor(self.collector)
        status = monitor.evaluate_status()
        
        self.assertIn("kernel_health", status)
        self.assertIn("health_score", status)
        
        # 50% success = -50 points. 1 error = -1.5 points. Score ~48 (CRITICAL)
        self.assertTrue(status["health_score"] <= 50)
        self.assertEqual(status["kernel_health"], "CRITICAL")
        
        # Vérification Index et PRAGMAs (via Storage)
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("PRAGMA journal_mode")
            self.assertEqual(cursor.fetchone()[0].lower(), "wal")
        finally:
            conn.close()

if __name__ == "__main__":
    unittest.main()
