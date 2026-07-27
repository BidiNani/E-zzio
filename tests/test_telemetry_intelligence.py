import unittest
import os
import tempfile
import shutil
import time
from runtime.telemetry import TelemetryStorage, TelemetryCollector, ExecutionMetric

class TestTelemetryIntelligence(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_intel.db")
        self.storage = TelemetryStorage(db_path=self.db_path)
        self.collector = TelemetryCollector(storage=self.storage, batch_size=10, flush_interval=0.1)
        self.collector.start()

    def tearDown(self):
        self.collector.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_health_endpoint_and_peak_size(self):
        for i in range(25):
            self.collector.record_execution(ExecutionMetric(f"ex_{i}", "intel_action", "SUCCESS", 15.0, 1.0, "LOW"))
            
        self.collector.flush()
        endpoint = self.collector.get_health_endpoint()
        
        self.assertEqual(endpoint["collector"], "healthy")
        self.assertEqual(endpoint["worker_status"], "ALIVE")
        self.assertEqual(endpoint["version"], "2.6.9")
        self.assertGreater(endpoint["queue_peak_size"], 0)
        self.assertGreater(endpoint["flush_count"], 0)

    def test_prometheus_and_otlp_exporters(self):
        self.collector.record_execution(
            ExecutionMetric("ex_100", "web_search", "SUCCESS", 120.0, 1.5, "LOW", trace_id="tr_1", span_id="sp_1")
        )
        self.collector.flush()
        
        # Test export Prometheus
        prom_text = self.storage.export_prometheus()
        self.assertIn("ezzio_executions_total", prom_text)
        self.assertIn("ezzio_success_rate", prom_text)
        
        # Test export OTLP
        otlp_spans = self.storage.export_otlp_spans(limit=10)
        self.assertEqual(len(otlp_spans), 1)
        self.assertEqual(otlp_spans[0]["traceId"], "tr_1")
        self.assertEqual(otlp_spans[0]["name"], "web_search")

if __name__ == "__main__":
    unittest.main()
