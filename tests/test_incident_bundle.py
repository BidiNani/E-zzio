import unittest
import os
import tempfile
import shutil
from dataclasses import replace
from runtime.recovery import IncidentBundleGenerator, IncidentStore, Severity, IncidentCategory
from runtime.telemetry import TelemetryCollector

class TestIncidentBundleEngine(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_incidents.db")
        self.export_dir = os.path.join(self.test_dir, "export")
        self.store = IncidentStore(db_path=self.db_path, export_dir=self.export_dir)
        self.collector = TelemetryCollector()
        self.generator = IncidentBundleGenerator(store=self.store, collector=self.collector)

    def tearDown(self):
        self.store.close()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_generate_and_persist_bundle_with_scores(self):
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
        self.assertEqual(bundle.severity_score, 70)
        self.assertTrue(bundle.verify_integrity())

        # Vérification Export JSON sur disque
        json_file = os.path.join(self.export_dir, f"{bundle.incident_id}.json")
        self.assertTrue(os.path.exists(json_file))

        # Vérification persistance SQLite
        retrieved = self.store.get_bundle(bundle.incident_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["severity_score"], 70)

    def test_bundle_integrity_failure(self):
        """Test de corruption : vérifie qu'une altération de champ invalide l'empreinte."""
        bundle = self.generator.generate_incident(
            execution_id="exec_sec_01",
            action_name="system_exec",
            severity=Severity.CRITICAL,
            category=IncidentCategory.SECURITY_CONTEXT_FAILURE,
            payload={"cmd": "rm -rf /"},
            context_signature_valid=False
        )

        self.assertTrue(bundle.verify_integrity())

        # Altération malveillante d'un champ
        corrupted_bundle = replace(bundle, severity="INFO")
        self.assertFalse(corrupted_bundle.verify_integrity())

if __name__ == "__main__":
    unittest.main()
