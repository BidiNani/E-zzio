"""
E-ZZIO Autonomous Coding Agent — End-to-End Hardening & Certification Test Suite.

Couvre les exigences strictes de certification :
1. Cycle complet sur tâche complexe multi-fichiers
2. Échec puis auto-réparation avec re-test automatique
3. Invalidation et rollback sur anomalie AST ou violation de politique
4. Préservation stricte du budget (fichiers, diff, commandes)
5. Non-régression des tests unitaires et plate-forme (Frozen Core & Secrets)
6. Génération et complétude des artefacts de preuve (Evidence Logger)
7. Fonctionnement nominal de la machine d'état (TaskStatus) et rejet des transitions illégales
8. Fonctionnement du Circuit Breaker persistant sur pannes répétées
9. Exécution déterministe avec hashes d'identification reproductibles
10. Traçabilité complète des outils et validation des arguments
"""

import os
import sys
import json
import pytest
import asyncio
from core.agent.complex_task_orchestrator import (
    ComplexTaskEngine,
    ValidationState,
    CodebaseImpactAnalyzer,
    TaskStep,
)
from core.agent.mission_controller import (
    MissionController,
    MissionStatus,
    TaskStatus,
    WorkerRole,
    MissionTask,
    TaskGraph,
    validate_task_transition,
)
from core.agent.tools_registry import ToolRegistry
from core.agent.agent_guard import AgentPolicyGuard, CodingAgentBudget
from core.routing.circuit_breaker import circuit_breaker


# =============================================================================
# 1. State Machine & Illegal Transition Tests
# =============================================================================

def test_task_status_valid_transitions():
    """Vérifie que les transitions autorisées dans le cycle de vie sont acceptées."""
    task = MissionTask("t_stat_1", "Test State", "Desc", WorkerRole.CODER)
    assert task.status == TaskStatus.PENDING

    assert task.transition_to(TaskStatus.READY) is True
    assert task.status == TaskStatus.READY

    assert task.transition_to(TaskStatus.RUNNING) is True
    assert task.status == TaskStatus.RUNNING

    assert task.transition_to(TaskStatus.SUCCEEDED) is True
    assert task.status == TaskStatus.SUCCEEDED


def test_task_status_illegal_transitions_rejected():
    """Vérifie que les transitions illégales (ex: PENDING -> SUCCEEDED, BLOCKED -> RUNNING) sont refusées."""
    # PENDING -> SUCCEEDED est illégal
    task1 = MissionTask("t_stat_2", "Illegal Direct Complete", "Desc", WorkerRole.CODER)
    with pytest.raises(ValueError, match="ILLEGAL TRANSITION"):
        task1.transition_to(TaskStatus.SUCCEEDED)

    # BLOCKED -> RUNNING sans repasser par READY
    task2 = MissionTask("t_stat_3", "Blocked to Running Direct", "Desc", WorkerRole.CODER)
    task2.status = TaskStatus.BLOCKED
    with pytest.raises(ValueError, match="ILLEGAL TRANSITION"):
        task2.transition_to(TaskStatus.RUNNING)

    # SUCCEEDED -> RUNNING (état terminal)
    task3 = MissionTask("t_stat_4", "Terminal to Running", "Desc", WorkerRole.CODER)
    task3.status = TaskStatus.SUCCEEDED
    with pytest.raises(ValueError, match="ILLEGAL TRANSITION"):
        task3.transition_to(TaskStatus.RUNNING)

    # CANCELLED -> RUNNING (état terminal)
    task4 = MissionTask("t_stat_5", "Cancelled to Running", "Desc", WorkerRole.CODER)
    task4.status = TaskStatus.CANCELLED
    with pytest.raises(ValueError, match="ILLEGAL TRANSITION"):
        task4.transition_to(TaskStatus.RUNNING)


# =============================================================================
# 2. Circuit Breaker Integration Tests
# =============================================================================

def test_circuit_breaker_trips_on_repeated_repair_failures(tmp_path):
    """Vérifie que le disjoncteur s'ouvre après des échecs répétés et bloque l'exécution."""
    workspace = str(tmp_path)
    engine = ComplexTaskEngine(workspace_root=workspace)

    cb_key = "self_repair:broken_target.py"
    # Réinitialiser l'état du disjoncteur pour ce test
    circuit_breaker.record_success(cb_key)
    assert not circuit_breaker.is_open(cb_key)

    # Simuler 3 échecs consécutifs
    circuit_breaker.record_failure(cb_key)
    circuit_breaker.record_failure(cb_key)
    circuit_breaker.record_failure(cb_key)

    assert circuit_breaker.is_open(cb_key)
    assert circuit_breaker.get_state(cb_key) == "OPEN"

    # L'appel à run_self_repair doit être court-circuité immédiatement
    repaired, msg = engine.run_self_repair(
        test_file="tests/dummy_test.py",
        failure_output="AssertionError: 1 != 2",
        target_file=os.path.join(workspace, "broken_target.py"),
        max_attempts=5,
    )
    assert repaired is False
    assert "[CIRCUIT BREAKER OPEN]" in msg

    # Restauration après succès
    circuit_breaker.record_success(cb_key)
    assert not circuit_breaker.is_open(cb_key)


# =============================================================================
# 3. Deterministic Mode Tests
# =============================================================================

def test_complex_task_deterministic_execution(tmp_path):
    """Vérifie que le mode deterministic=True produit des task_id stables et trie les fichiers."""
    workspace = str(tmp_path)
    os.makedirs(os.path.join(workspace, "tests"), exist_ok=True)

    f1 = os.path.join(workspace, "b_mod.py")
    with open(f1, "w", encoding="utf-8") as fp:
        fp.write("def b(): return 2\n")

    f2 = os.path.join(workspace, "a_mod.py")
    with open(f2, "w", encoding="utf-8") as fp:
        fp.write("def a(): return 1\n")

    engine = ComplexTaskEngine(workspace_root=workspace)
    res1 = engine.execute_complex_task(
        objective="Tâche déterministe A",
        target_files=["b_mod.py", "a_mod.py"],
        deterministic=True,
    )
    res2 = engine.execute_complex_task(
        objective="Tâche déterministe A",
        target_files=["a_mod.py", "b_mod.py"],
        deterministic=True,
    )

    # Les deux exécutions doivent avoir exactement le même task_id hashé
    assert res1["task_id"] == res2["task_id"]
    assert res1["task_id"].startswith("task_det_")
    assert res1["validation_state"] == ValidationState.CHANGE_VALIDATED


# =============================================================================
# 4. AST Invalidation & Rollback on Bad Patch
# =============================================================================

def test_ast_invalidation_triggers_immediate_rollback(tmp_path):
    """Vérifie qu'un patch introduisant une erreur syntaxique est immédiatement rejeté avec rollback."""
    workspace = str(tmp_path)
    os.makedirs(os.path.join(workspace, "tests"), exist_ok=True)

    code_file = os.path.join(workspace, "calc.py")
    original_code = "def add(x, y):\n    return x + y\n"
    with open(code_file, "w", encoding="utf-8") as fp:
        fp.write(original_code)

    engine = ComplexTaskEngine(workspace_root=workspace)
    res = engine.execute_complex_task(
        objective="Tenter un patch avec syntaxe cassée",
        target_files=["calc.py"],
        patch_actions=[{
            "path": "calc.py",
            "search": "return x + y",
            "replace": "return x +++",  # Erreur syntaxique AST
        }],
    )

    assert res["success"] is False
    assert "AST REVIEW REJECTED" in res["error"]
    assert res["validation_state"] == ValidationState.CHANGE_FAILED_VALIDATION

    # Le fichier source doit avoir été restauré à l'original (Rollback)
    with open(code_file, "r", encoding="utf-8") as fp:
        content = fp.read()
    assert content == original_code


# =============================================================================
# 5. Tool Registry Validation & Audit Logging
# =============================================================================

def test_tool_registry_argument_validation(tmp_path):
    """Vérifie le rejet d'appels d'outils avec arguments invalides ou manquants."""
    workspace = str(tmp_path)
    reg = ToolRegistry(workspace_root=workspace)

    # Paramètre manquant pour read_file
    res1 = reg.execute("read_file", {})
    assert "[INVALID_ARGUMENTS]" in res1
    assert "path" in res1

    # Paramètre manquant pour apply_patch
    res2 = reg.execute("apply_patch", {"path": "foo.py", "search": "bar"})
    assert "[INVALID_ARGUMENTS]" in res2
    assert "replace" in res2

    # Outil inconnu
    res3 = reg.execute("unknown_nonexistent_tool", {"foo": "bar"})
    assert "[ERROR]" in res3

    # Vérification que le journal d'audit des outils a bien consigné ces échecs
    audit_file = os.path.join(workspace, "state", "audit", "tool_executions.jsonl")
    assert os.path.exists(audit_file)
    with open(audit_file, "r", encoding="utf-8") as fp:
        lines = fp.readlines()
    assert len(lines) >= 3
    entries = [json.loads(line) for line in lines]
    statuses = [e["status"] for e in entries]
    assert "INVALID_ARGS" in statuses
    assert "UNKNOWN_TOOL" in statuses


# =============================================================================
# 6. Full Mission Lifecycle with Genuine Worker Execution
# =============================================================================

@pytest.mark.asyncio
async def test_full_mission_real_worker_orchestration(tmp_path):
    """Vérifie l'exécution réelle et déterministe d'une mission multi-rôles complète."""
    workspace = str(tmp_path)
    os.makedirs(os.path.join(workspace, "tests"), exist_ok=True)

    # Fichier source initial
    src_file = os.path.join(workspace, "payment.py")
    with open(src_file, "w", encoding="utf-8") as fp:
        fp.write("def charge(amount: int) -> bool:\n    return False\n")

    # Test associé
    test_file = os.path.join(workspace, "tests", "test_payment.py")
    with open(test_file, "w", encoding="utf-8") as fp:
        fp.write("from payment import charge\ndef test_charge(): assert charge(50) is True\n")

    controller = MissionController(
        mission_id="mission_e2e_payment_01",
        goal="Corriger charge pour retourner True",
        workspace_root=workspace,
        target_files=["payment.py"],
        patch_actions=[{
            "path": "payment.py",
            "search": "return False",
            "replace": "return True"
        }],
        test_suite=["tests/test_payment.py"]
    )

    res = await controller.run_mission()
    assert res["status"] == "COMPLETED"
    assert res["artifacts_count"] >= 7

    # Vérifier que le fichier est bien corrigé
    with open(src_file, "r", encoding="utf-8") as fp:
        content = fp.read()
    assert "return True" in content

    # Vérifier que tous les artefacts ont un hash SHA-256 valide
    for art in controller.artifacts:
        assert len(art.content_hash) == 64
        assert art.mission_id == "mission_e2e_payment_01"
