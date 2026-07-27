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
        self.assertEqual(summary["collector_version"], "2.6.8.2")
        self.assertGreater(summary["flush_count"], 0)
        
        json_export = self.storage.export_json(limit=10)
        self.assertIn("action_a", json_export)

    def test_health_state_matrix(self):
        monitor = HealthMonitor(self.collector)
        self.collector.record_execution(ExecutionMetric("ex_1", "action_a", "SUCCESS", 50.0, 0.5, "LOW"))
        
        self.collector.flush()
        status = monitor.evaluate_status()
        self.assertEqual(status["kernel_health"], "HEALTHY")
        self.assertEqual(status["health_score"], 100)

    def test_queue_pressure_survival(self):
        """Chaos Engineering : Saturation de la file avec 15000 événements ultra-rapides."""
        for i in range(15000):
            self.collector.record_execution(ExecutionMetric(f"ex_{i}", "chaos_action", "SUCCESS", 10.0, 1.0, "LOW"))
        
        self.collector.flush()
        summary = self.collector.get_summary()
        
        # Vérification 1 : Le système n'a pas deadlock et la file est purgée
        self.assertEqual(summary["queue_backlog"], 0)
        
        # Vérification 2 : Équation de conservation (Ce qui est entré = Ce qui est stocké + Ce qui est droppé)
        absorbed = summary["total_executions"]
        dropped = summary["dropped_metrics"]
        self.assertEqual(absorbed + dropped, 15000)
        
        # Vérification 3 : Le système a bien déclenché des flushs
        self.assertGreater(summary["flush_count"], 0)

if __name__ == "__main__":
    unittest.main()
