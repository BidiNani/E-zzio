import unittest
import os
import tempfile
import shutil
import gc
from runtime.telemetry import TelemetryStorage

class TestTelemetryStorage(unittest.TestCase):

    def setUp(self):
        # Création d'un dossier temporaire unique par test
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_telemetry.db")
        self.storage = TelemetryStorage(db_path=self.db_path)

    def tearDown(self):
        # Suppression explicite de l'instance pour libérer les références
        del self.storage
        
        # Forcer le ramasse-miettes pour clôturer tout handle orphelin sous Windows
        gc.collect()
        
        # Suppression récursive (inclut les fichiers .db, .db-wal, .db-shm)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_persistence_and_summary(self):
        self.storage.save_metric("ex_100", "web_search", "SUCCESS", 150.0, 1.0, "LOW")
        self.storage.save_metric("ex_101", "web_search", "ERROR", 300.0, 1.0, "LOW", category="TIMEOUT")

        summary = self.storage.get_summary()
        self.assertEqual(summary["total_executions"], 2)
        self.assertEqual(summary["success_rate"], 0.5)
        self.assertEqual(summary["mean_latency_ms"], 225.0)
        self.assertEqual(summary["error_breakdown"].get("TIMEOUT"), 1)

if __name__ == "__main__":
    unittest.main()
