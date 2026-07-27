import unittest
import tempfile
import shutil
import os
import time
from runtime.telemetry import TelemetryCollector, ExecutionMetric, HealthMonitor, TelemetryStorage

class TestTelemetrySystem(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_telemetry.db")
        self.storage = TelemetryStorage(db_path=self.db_path)
        
        self.collector = TelemetryCollector(storage=self.storage, batch_size=1, flush_interval=0.1)
        self.collector.start()

    def tearDown(self):
        self.collector.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_record_and_summary(self):
        self.collector.record_execution(ExecutionMetric("ex_1", "file_scan", "SUCCESS", 120.0, 1.0, "LOW"))
        self.collector.record_execution(ExecutionMetric("ex_2", "file_scan", "FAILED", 250.0, 1.0, "LOW", category="HANDLER_SIGNATURE_ERROR"))
        
        time.sleep(0.3)
        summary = self.collector.get_summary()
        self.assertEqual(summary["total_executions"], 2)
        self.assertEqual(summary["success_rate"], 0.5)
        self.assertEqual(summary["error_breakdown"].get("HANDLER_SIGNATURE_ERROR"), 1)

    def test_health_monitor(self):
        monitor = HealthMonitor(self.collector)
        self.collector.record_execution(ExecutionMetric("ex_1", "web_search", "SUCCESS", 50.0, 0.5, "LOW"))
        
        time.sleep(0.3)
        status = monitor.evaluate_status()
        self.assertEqual(status["kernel_health"], "HEALTHY")

if __name__ == "__main__":
    unittest.main()
