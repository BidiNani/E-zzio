import unittest
import os
from runtime.telemetry import TelemetryStorage, TelemetryCollector, ExecutionMetric

class TestTelemetryStorage(unittest.TestCase):

    def setUp(self):
        self.db_path = "data/test_telemetry.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.storage = TelemetryStorage(db_path=self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

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
