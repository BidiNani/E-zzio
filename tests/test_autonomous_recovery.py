import unittest
import os
import tempfile
import shutil
import gc
from runtime.recovery import (
    IncidentBundleGenerator, IncidentStore, Severity, IncidentCategory, AutonomousRecoveryEngine
)
from runtime.telemetry import TelemetryCollector

class TestAutonomousRecovery(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_recovery.db")
        self.export_dir = os.path.join(self.test_dir, "export")
        self.store = IncidentStore(db_path=self.db_path, export_dir=self.export_dir)
        self.collector = TelemetryCollector()
        self.generator = IncidentBundleGenerator(store=self.store, collector=self.collector)
        self.recovery_engine = AutonomousRecoveryEngine(db_path=self.db_path)

    def tearDown(self):
        self.store.close()
        # Forcer le garbage collector pour libérer tout handle SQLite résiduel
        gc.collect()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_remediation_policy_timeout(self):
        bundle = self.generator.generate_incident(
            execution_id="exec_t1",
            action_name="api_call",
            severity=Severity.HIGH,
            category=IncidentCategory.EXTERNAL_TIMEOUT,
            payload={"endpoint": "/pay"},
            context_signature_valid=True,
            error_details="Timeout"
        )

        action = self.recovery_engine.process_incident(bundle)
        self.assertEqual(action.action_type, "RETRY_BACKOFF")
        self.assertEqual(action.parameters.get("max_retries"), 3)

    def test_remediation_policy_security_quarantine(self):
        bundle = self.generator.generate_incident(
            execution_id="exec_sec_bad",
            action_name="admin_override",
            severity=Severity.CRITICAL,
            category=IncidentCategory.SECURITY_CONTEXT_FAILURE,
            payload={"hack": True},
            context_signature_valid=False,
            error_details="HMAC mismatch"
        )

        action = self.recovery_engine.process_incident(bundle)
        self.assertEqual(action.action_type, "QUARANTINE_HANDLER")
        self.assertEqual(action.confidence, 1.0)

if __name__ == "__main__":
    unittest.main()
