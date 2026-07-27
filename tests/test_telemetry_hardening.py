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
        self.collector = TelemetryCollector(storage=self.storage, batch_size=50, flush_interval=0.1)
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
        self.assertEqual(summary["collector_version"], self.collector.collector_version)
        self.assertGreater(summary["flush_count"], 0)

    def test_queue_pressure_survival(self):
        """Chaos Test : Injection massive et vérification de la conservation des compteurs atomiques."""
        for i in range(15000):
            self.collector.record_execution(ExecutionMetric(f"ex_{i}", "chaos_action", "SUCCESS", 10.0, 1.0, "LOW"))
        
        self.collector.flush()
        summary = self.collector.get_summary()
        
        self.assertEqual(summary["queue_backlog"], 0)
        absorbed = summary["total_executions"]
        dropped = summary["dropped_metrics"]
        self.assertEqual(absorbed + dropped, 15000)
        self.assertGreater(summary["flush_count"], 0)

if __name__ == "__main__":
    unittest.main()
