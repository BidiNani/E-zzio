import unittest
from runtime.core.microkernel import RuntimeBuilder
from runtime.tools.tool_schema import ToolRequest

class TestPhase6(unittest.TestCase):
    def setUp(self):
        self.builder = RuntimeBuilder().with_allowed_level(0)
        self.runtime = self.builder.build()

    def tearDown(self):
        self.runtime.stop()

    def test_git_status_external_executor(self):
        # Requête sans arguments (comme dicté par le schema)
        req = ToolRequest(name="git.status", arguments={})
        res = self.runtime.execute(req, "test_session")
        
        self.assertTrue(res.success, f"Le superviseur externe a échoué: {res.error}")
        self.assertIsNotNone(res.output)
        print(f"\n[GIT STATUS OUTPUT]\n{res.output}")

if __name__ == "__main__":
    unittest.main()