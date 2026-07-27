import unittest
import os
import tempfile
import shutil
import time
import gc
import sqlite3
from runtime.recovery import (
    IncidentBundleGenerator, IncidentStore, Severity, IncidentCategory, AutonomousRecoveryEngine, RecoveryLedger, RecoveryEventBus
)
from runtime.telemetry import TelemetryCollector

class TestRecoverySovereigntyLayer(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_sovereign.db")
        self.export_dir = os.path.join(self.test_dir, "export")
        self.store = IncidentStore(db_path=self.db_path, export_dir=self.export_dir)
        self.collector = TelemetryCollector()
        self.generator = IncidentBundleGenerator(store=self.store, collector=self.collector)
        self.ledger = RecoveryLedger(db_path=self.db_path)
        self.engine = AutonomousRecoveryEngine(collector=self.collector, recovery_ledger=self.ledger, db_path=self.db_path)

    def tearDown(self):
        self.store.close()
        gc.collect()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_environment_hmac_secret_override(self):
        os.environ["EZZIO_RECOVERY_HMAC_SECRET"] = "custom-override-secret-key-1234"
        bundle = self.generator.generate_incident(
            execution_id="exec_env_sec",
            action_name="test_act",
            severity=Severity.HIGH,
            category=IncidentCategory.EXTERNAL_TIMEOUT,
            payload={},
            context_signature_valid=True
        )
        custom_engine = AutonomousRecoveryEngine(collector=self.collector, db_path=self.db_path)
        res = custom_engine.process_incident(bundle)
        self.assertTrue(len(res["decision_signature"]) == 64)

    def test_recovery_ledger_immutable_entry(self):
        bundle = self.generator.generate_incident(
            execution_id="exec_ledger_1",
            action_name="batch_process",
            severity=Severity.HIGH,
            category=IncidentCategory.HANDLER_DEGRADATION,
            payload={"queue": 6000},
            context_signature_valid=True,
            error_details="CONGESTION"
        )
        res = self.engine.process_incident(bundle)
        self.assertEqual(res["execution_result"]["status"], "SUCCESS")

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("SELECT ledger_hash, action_type FROM recovery_ledger WHERE incident_id = ?", (bundle.incident_id,))
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[1], "SCALE_BATCH_SIZE")
            self.assertTrue(len(row[0]) == 64)
        finally:
            conn.close()

    def test_event_bus_overflow_sqlite_fallback(self):
        """Zero-Loss Test : Injection de 150 incidents dans une file RAM max 100."""
        processed_incidents = []
        
        def mock_processor(bundle):
            processed_incidents.append(bundle.incident_id)

        bus = RecoveryEventBus(incident_processor=mock_processor, db_path=self.db_path)
        bus.start()

        for i in range(150):
            bundle = self.generator.generate_incident(
                execution_id=f"exec_overflow_{i}",
                action_name="overflow_act",
                severity=Severity.INFO,
                category=IncidentCategory.EXTERNAL_TIMEOUT,
                payload={},
                context_signature_valid=True
            )
            bus.publish_incident(bundle)

        # Attente dynamique avec timeout 5s jusqu'à ce que les 150 événements soient traités
        start_time = time.time()
        while len(processed_incidents) < 150 and (time.time() - start_time < 5.0):
            time.sleep(0.05)

        bus.stop()
        self.assertEqual(len(processed_incidents), 150)

if __name__ == "__main__":
    unittest.main()
