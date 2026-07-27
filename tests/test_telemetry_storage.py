import unittest
import os
import tempfile
import shutil
import gc
from runtime.telemetry import TelemetryStorage, TelemetryCollector

class TestTelemetryStorage(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_telemetry.db")
        self.storage = TelemetryStorage(db_path=self.db_path)
        
        self.collector = TelemetryCollector()
        self.collector.configure_storage(self.storage)

    def tearDown(self):
        # Séparation propre et purge du singleton
        self.collector.configure_storage(None)
        TelemetryCollector.reset_instance()
        
        del self.storage
        gc.collect() # Force la libération du lock Windows
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_persistence_and_summary(self):
        self.storage.save_metric("ex_100", "web_search", "SUCCESS", 150.0, 1.0, "LOW")
        self.storage.save_metric("ex_101", "web_search", "ERROR", 300.0, 1.0, "LOW", category="TIMEOUT")

        summary = self.storage.get_summary()
        self.assertEqual(summary["total_executions"], 2)
        self.assertEqual(summary["success_rate"], 0.5)
        self.assertEqual(summary["mean_latency_ms"], 225.0)
        self.assertEqual(summary["error_breakdown"].get("TIMEOUT"), 1)

if __name__ == "__main__":
    unittest.main()
