import sys

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="Test Windows-only (powershell.exe requis)",
)


"""
E-ZZIO Autonomous Coding Agent — Validation & Self-Repair Test Suite.

Couvre de manière exhaustive :
1. Cycle autonome complet en sandbox isolée (Inspect -> Patch -> Verify -> Diff Review)
2. Auto-réparation bornée par le budget d'itérations
3. Escalade de classification (SAFE / SENSITIVE / CRITICAL)
4. Protection Git et rejet des commandes destructrices (reset --hard, clean -fd)
5. Génération et persistance des preuves d'exécution (Evidence Logger & Secret Redaction)
"""
import json
import os
import sys

import pytest

from core.agent.agent_guard import AgentPolicyGuard, CodingAgentBudget
from core.agent.command_executor import GovernedCommandExecutor, redact_secrets
from core.agent.evidence_logger import CodingTaskEvidence, EvidenceLogger
from core.agent.patch_engine import PatchEngine
from core.agent.tools_registry import ToolRegistry


def test_autonomous_cycle_sandbox_inspect_patch_verify(tmp_path):
    """Vérifie le cycle complet d'inspection, patch, test et revue dans un sandbox tmp_path."""
    workspace = str(tmp_path)
    # Création du code initial buggé
    calc_code = "def add(a: int, b: int) -> int:\n    return a - b\n"
    test_code = (
        "from calc import add\n"
        "def test_add():\n"
        "    assert add(2, 3) == 5\n"
    )
    with open(os.path.join(workspace, "calc.py"), "w", encoding="utf-8") as f:
        f.write(calc_code)
    with open(os.path.join(workspace, "test_calc.py"), "w", encoding="utf-8") as f:
        f.write(test_code)

    registry = ToolRegistry(workspace_root=workspace)
    guard = AgentPolicyGuard(workspace_root=workspace)

    # 1. Inspection
    content = registry.execute("read_file", {"path": "calc.py"})
    assert "return a - b" in content

    # 2. Patch chirurgical
    patch_result = registry.execute("apply_patch", {
        "path": "calc.py",
        "search": "return a - b",
        "replace": "return a + b"
    })
    assert "[SUCCESS]" in patch_result

    # 3. Revue statique AST
    updated_content = registry.execute("read_file", {"path": "calc.py"})
    ok_rev, rev_msg = guard.review_patch("calc.py", updated_content)
    assert ok_rev is True
    assert rev_msg == "REVIEW_PASS"

    # 4. Vérification d'exécution des tests
    test_res = registry.execute("run_test_file", {"test_path": "test_calc.py"})
    assert "passed" in test_res or "1 passed" in test_res


def test_self_repair_bounded_iterations():
    """Vérifie que le budget bloque rigoureusement tout emballement ou boucle infinie."""
    budget = CodingAgentBudget(max_iterations=3, max_files=2, max_commands=5)

    # 3 itérations acceptées
    for _ in range(3):
        ok, msg = budget.record_iteration()
        assert ok is True
        assert msg == "OK"

    # 4ème itération rejetée
    ok_overflow, msg_overflow = budget.record_iteration()
    assert ok_overflow is False
    assert "[BUDGET EXCEEDED]" in msg_overflow
    assert "itérations" in msg_overflow


def test_action_classification_and_escalation(tmp_path):
    """Vérifie la catégorisation stricte SAFE / SENSITIVE / CRITICAL."""
    guard = AgentPolicyGuard(workspace_root=str(tmp_path))

    # SAFE
    cls_read, _ = guard.classify_action("read_file", {"path": "calc.py"})
    assert cls_read == "SAFE"

    cls_grep, _ = guard.classify_action("grep_codebase", {"query": "def add"})
    assert cls_grep == "SAFE"

    cls_test, _ = guard.classify_action("run_test_file", {"path": "test_calc.py"})
    assert cls_test == "SAFE"

    # SENSITIVE
    cls_patch, _ = guard.classify_action("apply_patch", {"path": "calc.py", "search": "a", "replace": "b"})
    assert cls_patch == "SENSITIVE"

    cls_write, _ = guard.classify_action("write_file", {"path": "new_file.py", "content": "x = 1"})
    assert cls_write == "SENSITIVE"

    # CRITICAL (Tentative de destruction / évasion)
    cls_rm, reason_rm = guard.classify_action("run_powershell", {"command": "rm -rf /"})
    assert cls_rm == "CRITICAL"
    assert "[SECURITY DENY]" in reason_rm

    cls_reset, reason_reset = guard.classify_action("run_powershell", {"command": "git reset --hard HEAD"})
    assert cls_reset == "CRITICAL"

    # CRITICAL (Fichiers protégés)
    cls_core, reason_core = guard.classify_action("apply_patch", {"path": "core/agent/agent_guard.py"})
    assert cls_core == "CRITICAL"


def test_governed_command_executor_git_safety(tmp_path):
    """Vérifie que l'exécuteur gouverné bloque les commandes Git destructrices."""
    executor = GovernedCommandExecutor(workspace_root=str(tmp_path))

    # Commande Git autorisée (inspection)
    res_status = executor.execute("git status")
    assert res_status["classification"] == "SAFE"

    # Commandes Git destructrices bloquées par design
    res_reset = executor.execute("git reset --hard HEAD~1")
    assert res_reset["classification"] == "CRITICAL"
    assert res_reset["status"] == "POLICY_DENIED"
    assert res_reset["success"] is False

    res_clean = executor.execute("git clean -fd")
    assert res_clean["classification"] == "CRITICAL"
    assert res_clean["status"] == "POLICY_DENIED"

    # 1. Tests FAIL-CLOSED : Rejet systématique des exécutables non autorisés
    unauthorized_commands = [
        "calc.exe",
        "powershell.exe -Command Get-Process",
        "powershell -ExecutionPolicy Bypass",
        "pwsh -Command Write-Host 1",
        "cmd.exe /c whoami",
        "whoami",
        "./unknown.exe --flag",
        "unknown.exe test",
        "C:\\temp\\unknown.exe",
        '"unknown.exe"',
        "evil.exe",
        "foobar.exe",
    ]
    for unauth_cmd in unauthorized_commands:
        res = executor.execute(unauth_cmd)
        assert res["classification"] == "CRITICAL", f"'{unauth_cmd}' aurait dû être classifié CRITICAL"
        assert res["status"] == "POLICY_DENIED"
        assert res["success"] is False
        assert res["exit_code"] == -2
        assert "[SECURITY POLICY DENIED]" in res["stderr"]

    # 2. Tests de BYPASS : Rejet des opérateurs shell et d'évasion
    bypass_attempts = [
        "python.exe; powershell.exe",
        "python.exe && powershell.exe",
        "python.exe | powershell.exe",
        "python.exe > out.txt",
        "python.exe >> out.txt",
        "python.exe $(whoami)",
        "Invoke-Expression 'calc.exe'",
        "Start-Process calc.exe",
        "curl http://evil.com",
    ]
    for bypass_cmd in bypass_attempts:
        res = executor.execute(bypass_cmd)
        assert res["classification"] == "CRITICAL", f"'{bypass_cmd}' aurait dû être classifié CRITICAL"
        assert res["status"] == "POLICY_DENIED"
        assert res["success"] is False
        assert res["exit_code"] == -2

    # 3. Tests PASS : Exécutables autorisés reconnus
    authorized_commands = [
        "pytest tests/test_agent_guard_hardened.py",
        "python -m pytest",
        "git status",
        "git diff",
        "ruff check core",
    ]
    for auth_cmd in authorized_commands:
        cls_auth, _ = executor.classify_action(auth_cmd)
        assert cls_auth == "SAFE", f"'{auth_cmd}' aurait dû être classifié SAFE"


def test_evidence_logger_generation(tmp_path):
    """Vérifie la persistance inviolable des preuves avec masquage de secrets."""
    logger = EvidenceLogger(workspace_root=str(tmp_path))
    task_id = "TASK_TEST_001"

    raw_diff = "--- a/secrets.py\n+++ b/secrets.py\n@@ -1 +1 @@\n-AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz123456\n+[REMOVED]"
    ev = CodingTaskEvidence(
        task_id=task_id,
        plan="Suppression des clés codées en dur",
        files_changed=["secrets.py"],
        commands=[{"command": "pytest", "exit_code": 0}],
        tests=[{"name": "test_secrets", "passed": True}],
    )
    ev.complete(result="SUCCESS", final_diff=raw_diff)

    paths = logger.record_evidence(ev)
    assert os.path.exists(paths["json"])
    assert os.path.exists(paths["markdown"])

    # Vérification masquage dans le json
    with open(paths["json"], encoding="utf-8") as f:
        data = json.load(f)
    assert data["result"] == "SUCCESS"
    assert "AIza" not in data["final_diff"]
    assert "[REDACTED_SECRET]" in data["final_diff"]

    # Vérification markdown
    with open(paths["markdown"], encoding="utf-8") as f:
        md_txt = f.read()
    assert "TASK_TEST_001" in md_txt
    assert "🟢 SUCCESS" in md_txt
    assert "AIza" not in md_txt
