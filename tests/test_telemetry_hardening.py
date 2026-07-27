import unittest
import os
import tempfile
import shutil
import time
from runtime.telemetry import TelemetryStorage, TelemetryCollector, ExecutionMetric, HealthMonitor

class TestEnterpriseTelemetry(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_enterprise.db")
        self.storage = TelemetryStorage(db_path=self.db_path)
        self.collector = TelemetryCollector(storage=self.storage, flush_interval=0.1)
        self.collector.start()

    def tearDown(self):
        self.collector.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_loss_tracking_and_flush(self):
        self.collector.record_execution(ExecutionMetric("ex_1", "action_a", "SUCCESS", 100.0, 1.0, "LOW"))
        self.collector.record_execution(ExecutionMetric("ex_2", "action_b", "FAILED", 600.0, 1.0, "HIGH", category="TIMEOUT"))
        
        self.collector.flush()
        summary = self.collector.get_summary()
        
        self.assertEqual(summary["total_executions"], 2)
        self.assertEqual(summary["dropped_metrics"], 0)
        
        # Test export JSON pour Grafana
        json_export = self.storage.export_json(limit=10)
        self.assertIn("action_a", json_export)

    def test_health_state_matrix(self):
        monitor = HealthMonitor(self.collector)
        self.collector.record_execution(ExecutionMetric("ex_1", "action_a", "SUCCESS", 50.0, 0.5, "LOW"))
        
        self.collector.flush()
        status = monitor.evaluate_status()
        self.assertEqual(status["kernel_health"], "HEALTHY")
        self.assertEqual(status["health_score"], 100)

if __name__ == "__main__":
    unittest.main()
