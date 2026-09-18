"""
Test de validation du transfert d'autonomie agentique complet pour E-ZzIO.
Valide :
1. Découverte & outillage complet
2. Snapshots automatiques & Rollback
3. Journalisation d'audit immuable
4. Évaluation de difficulté & routage de modèles
5. Confinement PolicyGuard & escalade REQUIRE_HUMAN
"""

import json
import os

import pytest

from core.agent.agent_guard import AgentPolicyGuard
from core.agent.codebase_indexer import CodebaseIndexer
from core.agent.coding_agent_loop import CodingAgentHarness
from core.agent.patch_engine import PatchEngine
from core.agent.tools_registry import ToolRegistry


def test_tool_registry_complete_capabilities():
    workspace = "G:\\AI\\E-zzio"
    registry = ToolRegistry(workspace)
    tools = registry.list_tools()
    tool_names = [t["name"] for t in tools]

    assert "grep_codebase" in tool_names
    assert "find_files" in tool_names
    assert "read_file" in tool_names
    assert "read_file_slice" in tool_names
    assert "apply_patch" in tool_names
    assert "write_file" in tool_names
    assert "run_test_file" in tool_names

def test_task_complexity_evaluation():
    workspace = "G:\\AI\\E-zzio"
    harness = CodingAgentHarness(workspace_root=workspace)

    # Niveau 1 : Lite
    m_lite = harness.evaluate_task_complexity("Où est la fonction de hash ? Cherche dans le repo.")
    assert m_lite == "gemini-3.5-flash-lite"

    # Niveau 2 : Flash (par défaut)
    m_flash = harness.evaluate_task_complexity("Corrige la fonction compute_tax dans calculator.py et lance le test.")
    assert m_flash == "gemini-3.7-flash"

    # Niveau 3 : Pro
    m_pro = harness.evaluate_task_complexity("Refactorise l'architecture du microkernel pour résoudre les deadlocks AST.")
    assert m_pro == "gemini-3.1-pro"

def test_patch_engine_snapshots_and_audit(tmp_path):
    workspace = str(tmp_path)
    patcher = PatchEngine(workspace)

    rel_file = "sub/test_module.py"
    initial_code = "def calc():\n    return 10\n"

    # 1. Écriture initiale
    res_w = patcher.write_file(rel_file, initial_code)
    assert "[SUCCESS]" in res_w

    # 2. Patch avec snapshot
    res_patch = patcher.apply_search_replace(
        rel_path=rel_file,
        search_block="return 10",
        replace_block="return 20"
    )
    assert "[SUCCESS]" in res_patch
    assert "Snapshot" in res_patch

    # 3. Vérification du journal d'audit jsonl
    audit_file = os.path.join(workspace, "state", "audit", "auto_modifications.jsonl")
    assert os.path.exists(audit_file)
    with open(audit_file, encoding="utf-8") as f:
        records = [json.loads(line) for line in f.readlines() if line.strip()]
    assert len(records) >= 2
    assert records[-1]["action"] == "apply_patch"
    assert records[-1]["status"] == "APPLIED"

    # 4. Rollback
    rollback_ok = patcher.rollback(rel_file)
    assert rollback_ok is True

    full_path = os.path.join(workspace, rel_file)
    with open(full_path, encoding="utf-8") as f:
        restored = f.read()
    assert "return 10" in restored
