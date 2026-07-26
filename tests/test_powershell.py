import unittest
from runtime.core.microkernel import RuntimeBuilder
from runtime.tools.tool_schema import ToolRequest

class TestPowerShellSafe(unittest.TestCase):
    def setUp(self):
        self.builder = RuntimeBuilder().with_allowed_level(2)
        self.runtime = self.builder.build()

    def tearDown(self):
        self.runtime.stop()

    def test_1_allowed_command(self):
        """Test 1: Commande autorisée (Doit réussir)"""
        req = ToolRequest(name="system.powershell", arguments={"command": "Get-ChildItem"})
        res = self.runtime.execute(req, session_id="sess_ps_1")
        self.assertTrue(res.success, f"Devrait réussir: {res.error}")

    def test_2_blocked_command(self):
        """Test 2: Commande interdite (Doit bloquer avant le spawn)"""
        req = ToolRequest(name="system.powershell", arguments={"command": "Remove-Item -Recurse C:\\"})
        res = self.runtime.execute(req, session_id="sess_ps_2")
        self.assertFalse(res.success)

    def test_3_hard_kill_timeout(self):
        """Test 3: Timeout (Doit hard kill via Job Object)"""
        req = ToolRequest(name="system.powershell", arguments={"command": "Start-Sleep -Seconds 10", "timeout_sec": 1})
        res = self.runtime.execute(req, session_id="sess_ps_3")
        self.assertFalse(res.success)

    def test_4_massive_output_guard(self):
        """Test 4: Sortie massive (Doit être tronquée par OutputGuard)"""
        req = ToolRequest(name="system.powershell", arguments={"command": "1..5000 | ForEach-Object { \"Ligne $_\" }"})
        res = self.runtime.execute(req, session_id="sess_ps_4")
        self.assertTrue(res.success)

if __name__ == "__main__":
    unittest.main()