import unittest
import os
import tempfile
import shutil
import time
from runtime.telemetry import TelemetryStorage, TelemetryCollector, ExecutionMetric

class TestTelemetryStorage(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_telemetry.db")
        self.storage = TelemetryStorage(db_path=self.db_path)
        
        self.collector = TelemetryCollector(storage=self.storage, batch_size=1, flush_interval=0.1)
        self.collector.start()

    def tearDown(self):
        self.collector.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_persistence_and_summary(self):
        self.collector.record_execution(ExecutionMetric("ex_100", "web_search", "SUCCESS", 150.0, 1.0, "LOW"))
        self.collector.record_execution(ExecutionMetric("ex_101", "web_search", "ERROR", 300.0, 1.0, "LOW", category="TIMEOUT"))

        time.sleep(0.3)
        summary = self.storage.get_summary()
        self.assertEqual(summary["total_executions"], 2)
        self.assertEqual(summary["success_rate"], 0.5)
        self.assertEqual(summary["error_breakdown"].get("TIMEOUT"), 1)

if __name__ == "__main__":
    unittest.main()
