"""
Phase 2 Autonomy E2E Test Suite — Validation du transfert d'autonomie agentique complet.
"""

import os
import pytest
from core.agent.coding_agent_loop import CodingAgentHarness
from core.agent.patch_engine import PatchEngine
from core.agent.tools_registry import ToolRegistry


def test_antigravity_internal_tools_parity(tmp_path):
    """Vérifie la parité exacte des outils d'Antigravity dans le ToolRegistry d'E-ZZIO."""
    registry = ToolRegistry(workspace_root=str(tmp_path))
    tools = {t["name"]: t for t in registry.list_tools()}

    # Outils fondamentaux d'ingénierie
    expected_tools = [
        "grep_codebase",       # Équivalent de grep_search
        "find_files",          # Équivalent de find_by_name
        "read_file",           # Équivalent de view_file
        "read_file_slice",     # Équivalent de view_file avec StartLine/EndLine
        "apply_patch",         # Équivalent de replace_file_content avec snapshot
        "write_file",          # Équivalent de write_to_file
        "run_test_file",       # Équivalent de run_command pour pytest
    ]

    for tool_name in expected_tools:
        assert tool_name in tools, f"L'outil essentiel '{tool_name}' manque dans le ToolRegistry."


def test_autonomous_self_healing_and_patching(tmp_path):
    """Vérifie qu'E-ZZIO sait patcher un bug, sauvegarder un snapshot et valider le test."""
    workspace = tmp_path / "sandbox_dev"
    workspace.mkdir()

    # 1. Création d'un module avec un bug intentionnel
    src_dir = workspace / "src"
    src_dir.mkdir()
    math_py = src_dir / "math_utils.py"
    math_py.write_text(
        "def compute_discount(price: float, rate: float) -> float:\n"
        "    # Bug: addition au lieu de soustraction\n"
        "    return price + (price * rate)\n",
        encoding="utf-8"
    )

    # 2. Création du test unitaire qui échoue initialement
    tests_dir = workspace / "tests"
    tests_dir.mkdir()
    test_py = tests_dir / "test_math_utils.py"
    test_py.write_text(
        "import sys, os\n"
        "sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))\n"
        "from math_utils import compute_discount\n\n"
        "def test_discount():\n"
        "    assert compute_discount(100.0, 0.20) == 80.0\n",
        encoding="utf-8"
    )

    patcher = PatchEngine(workspace_root=str(workspace))

    # Étape A : Snapshot automatique avant patch
    snap = patcher.create_snapshot("src/math_utils.py")
    assert snap is not None
    assert os.path.exists(snap)

    # Étape B : Application du patch chirurgical
    search_block = "return price + (price * rate)"
    replace_block = "return price - (price * rate)"
    res_patch = patcher.apply_search_replace("src/math_utils.py", search_block, replace_block)
    assert "[SUCCESS]" in res_patch

    # Étape C : Vérification de l'exécution du test corrigé
    registry = ToolRegistry(workspace_root=str(workspace))
    test_res = registry.execute_tool("run_test_file", {"test_path": "tests/test_math_utils.py"})
    assert "[100%]" in test_res or "passed" in test_res.lower() or "ok" in test_res.lower()


def test_autonomous_rollback_on_failed_attempt(tmp_path):
    """Vérifie la restauration atomique (rollback) si un patch aggrave le code."""
    workspace = tmp_path / "rollback_test"
    workspace.mkdir()
    file_py = workspace / "service.py"
    original_code = "def start_service():\n    return 'OK_ORIGINAL'\n"
    file_py.write_text(original_code, encoding="utf-8")

    patcher = PatchEngine(workspace_root=str(workspace))
    patcher.create_snapshot("service.py")

    # Modification
    patcher.apply_search_replace("service.py", "'OK_ORIGINAL'", "'CORRUPTED'")
    assert "CORRUPTED" in file_py.read_text(encoding="utf-8")

    # Déclenchement du Rollback
    restored = patcher.rollback("service.py")
    assert restored is True
    assert file_py.read_text(encoding="utf-8") == original_code
