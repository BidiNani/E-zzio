import unittest
from pathlib import Path
from runtime.governance.decision import DecisionContract
from runtime.governance.gate import GovernanceGate


class TestGovernanceKernel(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path("G:/AI/E-zzio").resolve()
        self.gate = GovernanceGate(self.root_dir, autonomy_budget=50.0)

    def test_decision_spoof(self):
        d = DecisionContract("ID", "core", "action", "target", 0.1, {}, False, "time", "fake")
        res = self.gate.evaluate(d)
        self.assertEqual(res["status"], "DENIED")

    def test_budget_exhaustion(self):
        d = DecisionContract("ID", "core", "action", "target", 0.1, {"cost_units": 100}, False, "time", "")
        object.__setattr__(d, "signature", d.compute_fingerprint())
        res = self.gate.evaluate(d)
        self.assertEqual(res["status"], "DENIED")

    def test_domain_isolation(self):
        # Tentative d'accès interdit
        d = DecisionContract("ID", "core", "execute", "runtime/kernel", 0.99, {"cost_units": 1}, False, "time", "")
        object.__setattr__(d, "signature", d.compute_fingerprint())
        res = self.gate.evaluate(d)
        # Le RiskEngine devrait bloquer (score trop haut)
        self.assertEqual(res["status"], "DENIED")


if __name__ == "__main__":
    unittest.main()
