import unittest
from runtime.telemetry import TelemetryCollector, ExecutionMetric, HealthMonitor, TelemetryEvent, EventType

class TestTelemetrySystem(unittest.TestCase):

    def setUp(self):
        self.collector = TelemetryCollector()
        self.collector.reset()

    def test_record_and_summary(self):
        self.collector.record_execution(
            ExecutionMetric("ex_1", "file_scan", "SUCCESS", 120.0, 1.0, "LOW")
        )
        self.collector.record_execution(
            ExecutionMetric("ex_2", "file_scan", "ERROR", 250.0, 1.0, "LOW", category="HANDLER_SIGNATURE_ERROR")
        )

        summary = self.collector.get_summary()
        self.assertEqual(summary["total_executions"], 2)
        self.assertEqual(summary["success_rate"], 0.5)
        self.assertEqual(summary["mean_latency_ms"], 185.0)
        self.assertEqual(summary["error_breakdown"].get("HANDLER_SIGNATURE_ERROR"), 1)

    def test_health_monitor(self):
        monitor = HealthMonitor(self.collector)
        self.collector.record_execution(
            ExecutionMetric("ex_1", "web_search", "SUCCESS", 50.0, 0.5, "LOW")
        )

        status = monitor.evaluate_status()
        self.assertEqual(status["kernel_health"], "HEALTHY")

if __name__ == "__main__":
    unittest.main()
