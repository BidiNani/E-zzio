import unittest
import os
import tempfile
import shutil
import gc
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
        
        self.collector = TelemetryCollector()
        self.collector.configure_storage(self.storage)

    def tearDown(self):
        self.collector.configure_storage(None)
        TelemetryCollector.reset_instance()
        del self.storage
        gc.collect()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_schema_version_and_checksum(self):
        self.storage.save_event("evt_01", "TEST_EVENT", {"data": "test"}, time.time())
        
        conn = sqlite3.connect(self.db_path)
        try:
            # Vérification du schéma
            cursor = conn.execute("SELECT version FROM telemetry_schema ORDER BY version DESC LIMIT 1")
            self.assertEqual(cursor.fetchone()[0], 2)
            
            # Vérification de l'Evidence Chain (Checksum)
            cursor = conn.execute("SELECT checksum FROM telemetry_events WHERE event_id='evt_01'")
            checksum = cursor.fetchone()[0]
            self.assertTrue(len(checksum) == 64) # SHA-256 length
        finally:
            conn.close()

    def test_granular_health_score(self):
        monitor = HealthMonitor(self.collector)
        self.collector.record_execution(ExecutionMetric("ex_1", "action_a", "SUCCESS", 100.0, 1.0, "LOW"))
        self.collector.record_execution(ExecutionMetric("ex_2", "action_b", "FAILED", 600.0, 1.0, "HIGH", category="TIMEOUT"))
        
        status = monitor.evaluate_status()
        
        self.assertIn("kernel_health", status)
        self.assertIn("health_score", status)
        self.assertIn("signals", status)
        
        # 1 SUCCESS, 1 FAILED = 50% success rate -> score penalty of 50.
        # Mean latency is 350ms -> no latency penalty (threshold is 500).
        # 1 error -> pressure penalty of 2.
        # Base 100 - 50 - 2 = 48.
        self.assertEqual(status["health_score"], 48)
        self.assertEqual(status["kernel_health"], "CRITICAL")

if __name__ == "__main__":
    unittest.main()
