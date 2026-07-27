import unittest
import os
import tempfile
import shutil
import time
import gc
from runtime.recovery import (
    IncidentBundleGenerator, IncidentStore, Severity, IncidentCategory, AutonomousRecoveryEngine
)
from runtime.recovery.contracts import compute_decision_signature
from runtime.recovery.queue.bus import RecoveryEventBus
from runtime.telemetry import TelemetryCollector

class TestActiveRollbackAndSeal(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_active.db")
        self.export_dir = os.path.join(self.test_dir, "export")
        self.store = IncidentStore(db_path=self.db_path, export_dir=self.export_dir)
        self.collector = TelemetryCollector()
        self.generator = IncidentBundleGenerator(store=self.store, collector=self.collector)
        self.recovery_engine = AutonomousRecoveryEngine(collector=self.collector, db_path=self.db_path)

    def tearDown(self):
        self.store.close()
        gc.collect()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_active_rollback_execution(self):
        """Vérifie l'exécution d'une modification de batch_size puis son annulation effective via restore()."""
        self.assertEqual(self.collector.batch_size, 50)

        # Simulation d'un incident de congestion
        bundle = self.generator.generate_incident(
            execution_id="exec_congestion_1",
            action_name="batch_ingest",
            severity=Severity.HIGH,
            category=IncidentCategory.HANDLER_DEGRADATION,
            payload={"queue": 6000},
            context_signature_valid=True,
            error_details="CONGESTION: Critical queue backlog."
        )

        res = self.recovery_engine.process_incident(bundle)
        self.assertEqual(res["action_type"], "SCALE_BATCH_SIZE")
        self.assertEqual(self.collector.batch_size, 200) # Modification appliquée à chaud

        # Exécution du Rollback
        rb_id = res["rollback_record_id"]
        self.assertIsNotNone(rb_id)
        
        rollback_res = self.recovery_engine.rollback_manager.restore(rb_id, executors=self.recovery_engine.executors)
        self.assertEqual(rollback_res["status"], "SUCCESS")
        self.assertEqual(self.collector.batch_size, 50) # Batch size restauré

    def test_hmac_decision_signature_verification(self):
        """Vérifie la présence et la validité du scellé HMAC sur la décision."""
        bundle = self.generator.generate_incident(
            execution_id="exec_sec_seal",
            action_name="sys_call",
            severity=Severity.CRITICAL,
            category=IncidentCategory.SECURITY_CONTEXT_FAILURE,
            payload={"bad": "payload"},
            context_signature_valid=False
        )

        res = self.recovery_engine.process_incident(bundle)
        sig = res["decision_signature"]
        self.assertTrue(len(sig) == 64) # Signature SHA-256

    def test_dry_run_simulation_mode(self):
        """Vérifie que le mode Dry-Run simule l'action sans modifier l'état réel."""
        bundle = self.generator.generate_incident(
            execution_id="exec_dry",
            action_name="test_act",
            severity=Severity.HIGH,
            category=IncidentCategory.EXTERNAL_TIMEOUT,
            payload={},
            context_signature_valid=True
        )

        res = self.recovery_engine.process_incident(bundle, dry_run=True)
        self.assertEqual(res["execution_result"]["status"], "DRY_RUN_SIMULATED")
        self.assertIsNone(res.get("rollback_record_id"))

    def test_async_recovery_event_bus(self):
        """Vérifie la prise en charge asynchrone des incidents via le RecoveryEventBus."""
        processed = []
        
        def mock_processor(bundle):
            processed.append(bundle.incident_id)

        bus = RecoveryEventBus(incident_processor=mock_processor)
        bus.start()

        bundle = self.generator.generate_incident(
            execution_id="exec_async",
            action_name="async_task",
            severity=Severity.INFO,
            category=IncidentCategory.EXTERNAL_TIMEOUT,
            payload={},
            context_signature_valid=True
        )

        bus.publish_incident(bundle)
        time.sleep(0.3)
        bus.stop()

        self.assertEqual(len(processed), 1)
        self.assertEqual(processed[0], bundle.incident_id)

if __name__ == "__main__":
    unittest.main()
