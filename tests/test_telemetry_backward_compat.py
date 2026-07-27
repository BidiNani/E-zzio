import unittest
import tempfile
import shutil
import os
from runtime.telemetry import TelemetryCollector, TelemetryStorage

class TestTelemetryBackwardCompatibility(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "compat.db")
        self.storage = TelemetryStorage(db_path=self.db_path)

    def tearDown(self):
        del self.storage
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_old_constructor_signature(self):
        """Vérifie que l'ancienne signature (batch_size explicite) ne crashe pas."""
        collector = TelemetryCollector(
            storage=self.storage,
            batch_size=1,
            flush_interval=0.1
        )
        # Vérification API interne
        self.assertEqual(collector.batch_size, 1)
        
        # Vérification que le batching dynamique expose l'info dans le summary
        summary = collector.get_summary()
        self.assertIn("configured_batch_size", summary)
        self.assertEqual(summary["configured_batch_size"], 1)

if __name__ == "__main__":
    unittest.main()
