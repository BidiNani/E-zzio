import unittest
import os
import tempfile
import shutil
import gc
from runtime.recovery import (
    IncidentBundleGenerator, IncidentStore, Severity, IncidentCategory, AutonomousRecoveryEngine
)
from runtime.recovery.decision.governor import DecisionGovernor, ExecutionApproval
from runtime.telemetry import TelemetryCollector

class TestAutonomousRecovery(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_recovery.db")
        self.export_dir = os.path.join(self.test_dir, "export")
        self.store = IncidentStore(db_path=self.db_path, export_dir=self.export_dir)
        self.collector = TelemetryCollector()
        self.generator = IncidentBundleGenerator(store=self.store, collector=self.collector)
        self.recovery_engine = AutonomousRecoveryEngine(collector=self.collector, db_path=self.db_path)

    def tearDown(self):
        self.store.close()
        gc.collect()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_full_remediation_execution_and_rollback_log(self):
        bundle = self.generator.generate_incident(
            execution_id="exec_t1",
            action_name="api_call",
            severity=Severity.HIGH,
            category=IncidentCategory.EXTERNAL_TIMEOUT,
            payload={"endpoint": "/pay"},
            context_signature_valid=True,
            error_details="Timeout"
        )

        res = self.recovery_engine.process_incident(bundle)
        self.assertEqual(res["action_type"], "RETRY_BACKOFF")
        self.assertEqual(res["approval_status"], "SUPERVISED_EXECUTE")
        self.assertEqual(res["execution_result"]["status"], "SUCCESS")
        self.assertIsNotNone(res["rollback_record_id"])

    def test_governor_blocking_low_confidence_action(self):
        # Simulation d'un gouverneur très strict
        strict_gov = DecisionGovernor(auto_threshold=0.99, supervised_threshold=0.95)
        engine = AutonomousRecoveryEngine(governor=strict_gov, db_path=self.db_path)

        bundle = self.generator.generate_incident(
            execution_id="exec_low_conf",
            action_name="data_sync",
            severity=Severity.HIGH,
            category=IncidentCategory.EXTERNAL_TIMEOUT,
            payload={"batch": 10},
            context_signature_valid=True
        )

        res = engine.process_incident(bundle)
        # Confiance de RETRY_BACKOFF est 0.85 -> Refusé par le gouverneur strict (< 0.95)
        self.assertEqual(res["approval_status"], "REQUIRE_HUMAN_APPROVAL")
        self.assertEqual(res["execution_result"]["status"], "SKIPPED")

if __name__ == "__main__":
    unittest.main()
