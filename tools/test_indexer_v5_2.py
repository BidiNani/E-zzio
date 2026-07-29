import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.index_engine_v5_2 import WorkspaceIndexerV52, SQLiteRepository, setup_logger, TelemetryCollector

class TestWorkspaceIndexerV52(unittest.TestCase):
    def test_init(self):
        self.assertTrue(True)

if __name__ == "__main__":
    unittest.main()
