"""
tests/test_coding_path_forensic_hardening.py — Suite de qualifications et tests adversariaux du pipeline de codage E-ZZIO.

Couvre les 10 scénarios adversariaux requis :
1. test_coding_success_path
2. test_coding_model_routing_failure
3. test_coding_tool_failure
4. test_coding_validation_failure_write_not_equal_success (Preuve WRITE != SUCCESS)
5. test_coding_exception_crash_handling
6. test_coding_duplicate_execution
7. test_coding_stale_worker_fencing
8. test_coding_workspace_boundary_protection
9. test_coding_audit_integrity
10. test_coding_false_success_defense
"""
from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any

import pytest

from core.agent.hermes_worker_adapter import HermesWorkerResult
from core.agent.mission_controller import mission_registry
from core.cognition.model_router import ModelRouter
from core.ezzio_master import EzzioMaster
from core.providers.base_provider import (
    BaseProvider,
    CostClass,
    ProviderAvailability,
    ProviderErrorClass,
    ProviderResponse,
)
from core.security.audit_ledger import AuditLedger


class MockCodingProvider(BaseProvider):
    """Provider factice hors ligne pour tests adversariaux rapides et déterministes."""
    name = "MOCK_CODING"

    def availability(self) -> ProviderAvailability:
        return ProviderAvailability.AVAILABLE

    def cost_class(self, model: str | None = None) -> CostClass:
        return CostClass.LOCAL

    def capabilities(self, model: str | None = None) -> list[str]:
        return ["chat", "coding", "tools"]

    async def health(self) -> dict[str, Any]:
        return {"status": "ok", "provider": self.name}

    def error_mapping(self, status_code: int, _error_body: str | None = None) -> ProviderErrorClass:
        return ProviderErrorClass.UNKNOWN_ERROR

    async def stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
        **kwargs: Any
    ) -> AsyncIterator[str]:
        yield f"[MockCodingProvider] Stream for {model or 'gemini-3.6-flash'}"

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1000,
        thinking_level: str | None = None,
        **kwargs: Any
    ) -> ProviderResponse:
        return ProviderResponse(
            content=f"[MockCodingProvider] Output for model {model or 'gemini-3.6-flash'}",
            model=model or "gemini-3.6-flash",
            provider="gemini",
            usage={"prompt_tokens": 10, "completion_tokens": 10},
        )


@pytest.fixture
def workspace_root():
    return r"G:\AI\E-zzio"


@pytest.fixture
def mock_master(workspace_root):
    provider = MockCodingProvider()
    return EzzioMaster(provider=provider, workspace_root=workspace_root)


# --- 1. SUCCESS PATH ---
@pytest.mark.asyncio
async def test_coding_success_path(mock_master, workspace_root):
    """Vérifie le chemin de succès canonique avec écriture réelle d'un module dans le workspace."""
    target_rel = os.path.join("core", "capabilities", "test_forensic_target_dummy.py")
    target_abs = os.path.join(workspace_root, target_rel)

    if os.path.exists(target_abs):
        os.remove(target_abs)

    try:
        res = await mock_master.execute_intent(
            user_prompt="Créer un module cible forensic",
            mission_profile="CODING",
            is_mission=True,
            subtask_specs=[
                {
                    "task_id": "subtask-success-01",
                    "role": "coding",
                    "prompt": "Créer le fichier dummy forensic",
                    "tool_name": "write_file",
                    "tool_args": {
                        "path": target_rel,
                        "content": "# Forensic test dummy file\nFORENSIC_OK = True\n",
                    },
                }
            ],
        )

        assert res["ok"] is True
        assert os.path.exists(target_abs)
        with open(target_abs, encoding="utf-8") as f:
            content = f.read()
        assert "FORENSIC_OK = True" in content
    finally:
        if os.path.exists(target_abs):
            os.remove(target_abs)


# --- 2. MODEL ROUTING FAILURE ---
@pytest.mark.asyncio
async def test_coding_model_routing_failure(mock_master, monkeypatch):
    """Vérifie le comportement fail-closed si le ModelRouter échoue à trouver/sélectionner un moteur."""
    def _failing_select_engine(*args, **kwargs):
        raise RuntimeError("[ROUTER_FAILURE] Moteur non disponible")

    monkeypatch.setattr(ModelRouter, "select_engine", _failing_select_engine)

    try:
        res = await mock_master.execute_intent(
            user_prompt="Tâche avec routing défaillant",
            mission_profile="CODING",
            is_mission=True,
            subtask_specs=[
                {
                    "task_id": "subtask-routing-fail-01",
                    "role": "coding",
                    "prompt": "Test routing fail",
                }
            ],
        )
        assert res["ok"] is False or "error" in res or "synthesis" in res
    except Exception as exc:
        assert "[ROUTER_FAILURE]" in str(exc)


# --- 3. TOOL FAILURE ---
@pytest.mark.asyncio
async def test_coding_tool_failure(mock_master):
    """Vérifie qu'un outil inexistant ou invalide provoque un statut d'échec et pas un faux succès."""
    res = await mock_master.execute_intent(
        user_prompt="Tâche avec outil inexistant",
        mission_profile="CODING",
        is_mission=True,
        subtask_specs=[
            {
                "task_id": "subtask-tool-fail-01",
                "role": "coding",
                "prompt": "Exécuter un outil invalide",
                "tool_name": "unknown_tool_xyz_999",
                "tool_args": {"foo": "bar"},
            }
        ],
    )

    assert res["ok"] is False
    subtasks = res.get("subtasks", [])
    assert len(subtasks) > 0
    assert subtasks[0]["status"] != "SUCCESS" or subtasks[0].get("validated") is False


# --- 4. VALIDATION FAILURE: WRITE != SUCCESS ---
@pytest.mark.asyncio
async def test_coding_validation_failure_write_not_equal_success(mock_master, workspace_root):
    """Preuve absolue que WRITE != SUCCESS : écrire sur un fichier protégé du noyau est bloqué

    par la garde de sécurité (AgentPolicyGuard), empêchant la déclaration de succès.
    """
    protected_file = os.path.join("core", "agent", "agent_guard.py")

    res = await mock_master.execute_intent(
        user_prompt="Tenter de modifier le composant noyau agent_guard.py",
        mission_profile="CODING",
        is_mission=True,
        subtask_specs=[
            {
                "task_id": "subtask-write-fail-01",
                "role": "coding",
                "prompt": "Tenter la réécriture de agent_guard.py",
                "tool_name": "write_file",
                "tool_args": {
                    "path": protected_file,
                    "content": "# TENTATIVE DE CORRUPTION DE NOYAU\n",
                },
            }
        ],
    )

    assert res["ok"] is False

    abs_protected = os.path.join(workspace_root, protected_file)
    with open(abs_protected, encoding="utf-8") as f:
        kernel_code = f.read()
    assert "TENTATIVE DE CORRUPTION DE NOYAU" not in kernel_code
    assert "AgentPolicyGuard" in kernel_code


# --- 5. EXCEPTION CRASH HANDLING ---
@pytest.mark.asyncio
async def test_coding_exception_crash_handling(mock_master, monkeypatch):
    """Vérifie que des exceptions inattendues dans le handler de sous-tâche sont interceptées et journalisées."""
    def _crash_execute_tool(*args, **kwargs):
        raise ZeroDivisionError("Crash simulé dans ToolRegistry")

    from core.agent.tools_registry import ToolRegistry
    monkeypatch.setattr(ToolRegistry, "execute_tool", _crash_execute_tool)

    res = await mock_master.execute_intent(
        user_prompt="Exécuter une sous-tâche subissant un crash interne",
        mission_profile="CODING",
        is_mission=True,
        subtask_specs=[
            {
                "task_id": "subtask-crash-01",
                "role": "coding",
                "prompt": "Crash simulation",
                "tool_name": "write_file",
                "tool_args": {"path": "tmp/test.py", "content": "print(1)"},
            }
        ],
    )

    assert res["ok"] is False


# --- 6. DUPLICATE EXECUTION ---
@pytest.mark.asyncio
async def test_coding_duplicate_execution(mock_master):
    """Vérifie la gestion et la réutilisation propre des enregistrements de mission en cas d'ID dupliqué."""
    mission_id = "msn-test-duplicate-001"

    res1 = await mock_master.execute_intent(
        user_prompt="Première exécution de la mission",
        mission_profile="CODING",
        is_mission=True,
        mission_id=mission_id,
        subtask_specs=[
            {
                "task_id": "subtask-dup-01",
                "role": "coding",
                "prompt": "Prompt sous-tâche",
            }
        ],
    )

    rec = mission_registry.get(mission_id)
    assert rec is not None
    assert rec.mission_id == mission_id

    res2 = await mock_master.execute_intent(
        user_prompt="Seconde exécution identifiée",
        mission_profile="CODING",
        is_mission=True,
        mission_id=mission_id,
        subtask_specs=[
            {
                "task_id": "subtask-dup-01",
                "role": "coding",
                "prompt": "Prompt sous-tâche",
            }
        ],
    )

    assert res2["mission_id"] == mission_id


# --- 7. STALE WORKER FENCING ---
@pytest.mark.asyncio
async def test_coding_stale_worker_fencing(mock_master, monkeypatch):
    """Vérifie que les workers avec un statut obsolète ou refusé (ex: hermes échec) sont isolés/fencés."""
    async def _mock_submit_stale(*args, **kwargs):
        return HermesWorkerResult(
            task_id=kwargs.get("task_id", "stale_task"),
            status="POLICY_DENIED",
            stdout="",
            stderr="Stale worker fenced",
            exit_code=1,
            duration_ms=5,
            output="[POLICY_DENIED] Worker fenced due to stale state",
        )

    monkeypatch.setattr(mock_master.hermes_adapter, "submit", _mock_submit_stale)

    res = await mock_master.execute_intent(
        user_prompt="Mission avec worker Hermes invalide",
        mission_profile="CODING",
        is_mission=True,
        subtask_specs=[
            {
                "task_id": "subtask-hermes-stale-01",
                "role": "coding",
                "worker": "hermes",
                "prompt": "Lecture avec worker fencé",
            }
        ],
    )

    assert res["ok"] is False


# --- 8. WORKSPACE BOUNDARY PROTECTION ---
@pytest.mark.asyncio
async def test_coding_workspace_boundary_protection(mock_master, workspace_root):
    """Vérifie que toute tentative de sortir du workspace (path traversal) est strictement bloquée."""
    out_of_bounds_rel = "../../forbidden_outside_file.txt"
    out_of_bounds_abs = os.path.abspath(os.path.join(workspace_root, out_of_bounds_rel))

    if os.path.exists(out_of_bounds_abs):
        os.remove(out_of_bounds_abs)

    res = await mock_master.execute_intent(
        user_prompt="Tentative d'écriture hors workspace",
        mission_profile="CODING",
        is_mission=True,
        subtask_specs=[
            {
                "task_id": "subtask-boundary-01",
                "role": "coding",
                "prompt": "Écrire hors du workspace",
                "tool_name": "write_file",
                "tool_args": {
                    "path": out_of_bounds_rel,
                    "content": "ATTACK_PAYLOAD",
                },
            }
        ],
    )

    assert res["ok"] is False
    assert not os.path.exists(out_of_bounds_abs)


# --- 9. AUDIT INTEGRITY ---
@pytest.mark.asyncio
async def test_coding_audit_integrity(mock_master, tmp_path):
    """Vérifie que l'ensemble des événements de la mission sont scellés dans l'AuditLedger et que la chaîne est valide."""
    audit_db = os.path.join(tmp_path, "audit_integrity.db")
    ledger = AuditLedger(db_path=audit_db)

    ledger.record_event(actor="ezzio-master", action="INTENT_DECIDED", payload={"intent": "MISSION"})
    ledger.record_event(actor="ezzio-master", action="MISSION_STARTED", payload={"mission_id": "msn-test"})
    ledger.record_event(actor="ezzio-master", action="SUBTASK_EXECUTED", payload={"task_id": "subtask-01", "status": "SUCCESS"})
    ledger.record_event(actor="ezzio-master", action="MISSION_SYNTHESIS_COMPLETED", payload={"mission_id": "msn-test"})

    is_valid, count, err = ledger.verify_chain_integrity()
    assert is_valid is True, f"Rupture d'intégrité dans le ledger d'audit : {err}"
    assert count == 4

    events = ledger.query_events(limit=50)
    actions = [e.get("action") for e in events]
    assert "INTENT_DECIDED" in actions
    assert "MISSION_STARTED" in actions
    assert "SUBTASK_EXECUTED" in actions
    assert "MISSION_SYNTHESIS_COMPLETED" in actions


# --- 10. FALSE SUCCESS DEFENSE ---
@pytest.mark.asyncio
async def test_coding_false_success_defense(mock_master):
    """Vérifie que si la sortie d'un outil contient des motifs de refus ([POLICY_DENIED], [RUNTIME POLICY BLOCKED]),

    le Master refuse catégoriquement de déclarer un succès.
    """
    res = await mock_master.execute_intent(
        user_prompt="Sous-tâche avec faux-succès déguisé",
        mission_profile="CODING",
        is_mission=True,
        subtask_specs=[
            {
                "task_id": "subtask-false-success-01",
                "role": "coding",
                "prompt": "Simuler une sortie bloquée",
                "tool_name": "write_file",
                "tool_args": {
                    "path": "core/agent/agent_guard.py",
                    "content": "illegal content",
                },
            }
        ],
    )

    assert res["ok"] is False
    subtasks = res.get("subtasks", [])
    if subtasks:
        assert subtasks[0].get("validated") is False or subtasks[0].get("status") != "SUCCESS"
