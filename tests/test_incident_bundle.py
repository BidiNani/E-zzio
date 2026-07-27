import unittest
import os
import tempfile
import shutil
from runtime.recovery import IncidentBundleGenerator, IncidentStore, Severity, IncidentCategory
from runtime.telemetry import TelemetryCollector

class TestIncidentBundleEngine(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_incidents.db")
        self.store = IncidentStore(db_path=self.db_path)
        self.collector = TelemetryCollector()
        self.generator = IncidentBundleGenerator(store=self.store, collector=self.collector)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_generate_and_persist_timeout_incident(self):
        payload = {"url": "https://api.external.com/data", "timeout": 5}
        bundle = self.generator.generate_incident(
            execution_id="exec_9988",
            action_name="web_fetch",
            severity=Severity.HIGH,
            category=IncidentCategory.EXTERNAL_TIMEOUT,
            payload=payload,
            context_signature_valid=True,
            error_details="Action 'web_fetch' timed out after 5.0s"
        )

        self.assertTrue(bundle.incident_id.startswith("inc_"))
        self.assertEqual(bundle.severity, "HIGH")
        self.assertEqual(bundle.category, "EXTERNAL_TIMEOUT")
        self.assertEqual(len(bundle.payload_hash), 64) # SHA-256

        # Vérification persistance SQLite
        retrieved = self.store.get_bundle(bundle.incident_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["execution_id"], "exec_9988")
        self.assertEqual(retrieved["context_valid"], True)

    def test_security_tampering_incident(self):
        bundle = self.generator.generate_incident(
            execution_id="exec_sec_01",
            action_name="system_exec",
            severity=Severity.CRITICAL,
            category=IncidentCategory.SECURITY_CONTEXT_FAILURE,
            payload={"cmd": "rm -rf /"},
            context_signature_valid=False,
            error_details="ExecutionContext tampered"
        )

        self.assertEqual(bundle.severity, "CRITICAL")
        self.assertIn("SECURITY_VIOLATION: Context signature tampered or invalid HMAC.", bundle.root_candidates[0])

if __name__ == "__main__":
    unittest.main()
