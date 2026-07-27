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

    def test_full_bundle_integrity_verification(self):
        payload = {"url": "https://api.external.com/data", "timeout": 5}
        bundle = self.generator.generate_incident(
            execution_id="exec_9988",
            action_name="web_fetch",
            severity=Severity.HIGH,
            category=IncidentCategory.EXTERNAL_TIMEOUT,
            payload=payload,
            context_signature_valid=True,
            trace_id="tr_1001",
            span_id="sp_2002",
            error_details="Action 'web_fetch' timed out after 5.0s"
        )

        self.assertTrue(bundle.verify_integrity())

        # Test de corruption sur champ racine
        corrupted_1 = replace(bundle, root_candidates=["TAMPERED_ROOT_CAUSE"])
        self.assertFalse(corrupted_1.verify_integrity())

        # Test de corruption sur snapshot télémétrie
        corrupted_2 = replace(bundle, telemetry_snapshot={"fake": "data"})
        self.assertFalse(corrupted_2.verify_integrity())

        # Test de corruption sur metadata
        corrupted_3 = replace(bundle, metadata={"hacked": True})
        self.assertFalse(corrupted_3.verify_integrity())

    def test_json_export_and_sqlite_store(self):
        bundle = self.generator.generate_incident(
            execution_id="exec_sec_01",
            action_name="system_exec",
            severity=Severity.CRITICAL,
            category=IncidentCategory.SECURITY_CONTEXT_FAILURE,
            payload={"cmd": "rm -rf /"},
            context_signature_valid=False
        )

        # Vérification fichier JSON physique
        export_file = os.path.join(self.export_dir, f"{bundle.incident_id}.json")
        self.assertTrue(os.path.exists(export_file))

        # Vérification stockage SQLite
        retrieved = self.store.get_bundle(bundle.incident_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["severity_score"], 100)

if __name__ == "__main__":
    unittest.main()
