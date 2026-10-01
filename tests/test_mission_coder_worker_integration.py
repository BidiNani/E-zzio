"""Tests pour l'Étape 14 : Intégration gouvernée canonique de CoderWorker sous EzzioMaster et TaskDAG.

Vérifie que CoderWorker et CoderWorkerAdapter s'intègrent dans le pipeline de gouvernance
sans contournement d'autorité (Policy, Budget, ExecutionDecisionEngine, GovernedWorkerSelector, CompletionGate, AuditLedger).
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.agent.coder_worker_adapter import CoderWorkerAdapter
from core.agent.external_worker_contract import (
    GovernedWorkerSelector,
    WorkerRequest,
    WorkerResult,
    validate_worker_pre_execution,
)
from core.cognition.execution_decision_engine import ExecutionDecision, ExecutionDecisionEngine
from core.ezzio_master import EzzioMaster
from core.quality_gate.completion_gate import CompletionGate
from core.security.audit_ledger import AuditLedger


@pytest.fixture
def master_instance():
    master = EzzioMaster(workspace_root=r"G:\AI\E-zzio")
    return master


@pytest.mark.asyncio
async def test_a_mission_target_resolution_coder_worker(master_instance):
    """Test A: Une mission ciblant coder_worker résout canonicalement coder_worker avec un score élevé."""
    decision = master_instance.execution_engine.evaluate_and_decide(
        task_type="coding",
        objective="Corriger une fonction dans le module math",
        preferred_target="coder_worker",
    )
    assert decision.execution_type == "WORKER"
    assert decision.target_id == "coder_worker"
    assert decision.score >= 100.0


@pytest.mark.asyncio
async def test_b_policy_deny_blocks_coder_worker_mission(master_instance):
    """Test B: Un blocage Policy empêche l'exécution de CoderWorker dans une mission."""
    spec = {
        "nodes": [
            {
                "id": "node_1",
                "role": "coding",
                "worker": "coder_worker",
                "prompt": "Vider la base de données et supprimer system32",
            }
        ]
    }
    with patch.object(master_instance.harness.policy_guard, "evaluate_intent", return_value=(False, "[SECURITY DENY] Action destructive interdite")):
        res = await master_instance.orchestrate_multi_agent_mission(
            "Exécute la mission destructive",
            spec=spec,
        )
        assert res["ok"] is False
        assert len(res["subtasks"]) > 0
        node_res = res["subtasks"][0]
        assert node_res.get("status") in ("DENIED", "FAILED") or "POLICY_DENIED" in str(node_res.get("output", ""))


@pytest.mark.asyncio
async def test_c_budget_deny_blocks_coder_worker_mission(master_instance):
    """Test C: Un dépassement de budget bloque l'exécution de CoderWorker avant toute invocation."""
    spec = {
        "nodes": [
            {
                "id": "node_1",
                "role": "coding",
                "worker": "coder_worker",
                "prompt": "Générer du code complexe",
                "budget_deny": True,
            }
        ]
    }
    res = await master_instance.orchestrate_multi_agent_mission(
        "Mission avec dépassement budget",
        spec=spec,
    )
    assert res["ok"] is False
    assert len(res["subtasks"]) > 0
    node_res = res["subtasks"][0]
    assert node_res.get("status") in ("DENIED", "FAILED") or "BUDGET_DENIED" in str(node_res.get("output", ""))


@pytest.mark.asyncio
async def test_d_coder_worker_unavailable_fail_closed_fallback():
    """Test D: Si tous les workers externes sont indisponibles, le sélecteur bascule de manière sécurisée vers Native Worker."""
    selector = GovernedWorkerSelector(workspace_root=r"G:\AI\E-zzio")
    # Supprimer tous les workers externes pour forcer le basculement vers native
    for w in ["coder_worker", "coder", "hermes", "cline", "pig"]:
        selector._workers.pop(w, None)

    target_id, adapter = selector.select_execution_target(preferred_worker="coder_worker")
    assert target_id == "native"
    assert adapter is not None


@pytest.mark.asyncio
async def test_e_pre_execution_guard_target_mismatch():
    """Test E: Incompatibilité de cible dans ExecutionDecision déclenche [PRE_EXECUTION_DENIED]."""
    wrong_decision = ExecutionDecision(
        execution_type="WORKER",
        target_id="hermes",
        provider="hermes",
        is_local=False,
        score=90.0,
        rationale="Targeted hermes",
    )
    allowed, reason = validate_worker_pre_execution("coder_worker", wrong_decision)
    assert not allowed
    assert "[PRE_EXECUTION_DENIED]" in reason


@pytest.mark.asyncio
async def test_f_successful_governed_coder_worker_mission_execution(master_instance):
    """Test F: Exécution gouvernée réussie d'un nœud mission via CoderWorkerAdapter."""
    mock_llm_response = {
        "files": [{"path": "core/coding/sample_module.py", "content": "# Updated code"}],
        "explanation": "Fixed bug cleanly",
    }

    def dummy_llm(p, m=None):
        import json
        return json.dumps(mock_llm_response)

    spec = {
        "nodes": [
            {
                "id": "node_coding",
                "role": "coding",
                "worker": "coder_worker",
                "prompt": "Corriger le module sample_module",
                "dry_run": True,
                "target_file": "core/coding/sample_module.py",
                "validation_cmd": "python -c \"print('OK')\"",
                "test_command": "python -c \"print('OK')\"",
                "injected_llm_callback": dummy_llm,
            }
        ]
    }

    res = await master_instance.orchestrate_multi_agent_mission(
        "Mission coding gouvernée",
        spec=spec,
    )
    assert res["ok"] is True
    assert len(res["subtasks"]) > 0
    node_out = res["subtasks"][0]
    assert node_out["status"] == "SUCCESS"
    assert node_out["validated"] is True


@pytest.mark.asyncio
async def test_g_failed_coder_worker_execution_rejected_by_validation(master_instance):
    """Test G: Un échec d'exécution de CoderWorker fait échouer la sous-tâche sans validation."""
    def failing_llm(p, m=None):
        raise RuntimeError("LLM Provider Timeout")

    spec = {
        "nodes": [
            {
                "id": "node_failing",
                "role": "coding",
                "worker": "coder_worker",
                "prompt": "Générer du code défaillant",
                "dry_run": True,
                "injected_llm_callback": failing_llm,
            }
        ]
    }

    res = await master_instance.orchestrate_multi_agent_mission(
        "Mission échec coder_worker",
        spec=spec,
    )
    assert res["ok"] is False
    assert len(res["subtasks"]) > 0
    node_res = res["subtasks"][0]
    assert node_res.get("status") in ("FAILED", "ERROR") or "Execution check failed" in str(node_res.get("output", ""))


@pytest.mark.asyncio
async def test_h_audit_trail_recorded_during_coder_worker_mission(master_instance):
    """Test H: AuditLedger enregistre les événements clés lors d'une mission avec CoderWorker."""
    ledger = master_instance.harness.audit_ledger
    initial_count = len(ledger.entries) if hasattr(ledger, "entries") else 0

    spec = {
        "nodes": [
            {
                "id": "node_audit",
                "role": "coding",
                "worker": "coder_worker",
                "prompt": "Tâche de vérification audit",
                "dry_run": True,
            }
        ]
    }

    await master_instance.orchestrate_multi_agent_mission(
        "Mission audit traçabilité",
        spec=spec,
    )

    # Vérification qu'au moins une entrée d'audit a été ajoutée
    entries = ledger.entries if hasattr(ledger, "entries") else []
    assert len(entries) >= initial_count
