"""Tests for E-ZZIO Step 6 — Mission & TaskDAG Canonical Governance Alignment."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.cognition.execution_decision_engine import ExecutionDecision
from core.ezzio_master import EzzioMaster
from core.orchestration.dag import DAGExecutionStatus, DAGNode
from core.providers.base_provider import ProviderResponse


@pytest.fixture
def dummy_provider():
    provider = MagicMock()
    provider.name = "gemini"
    provider.is_available.return_value = True
    provider.generate = AsyncMock(return_value=ProviderResponse(
        content="Mission step output",
        model="gemini-2.5-flash",
        provider="gemini",
    ))
    return provider


@pytest.mark.asyncio
async def test_mission_node_default_policy_decision_untested():
    """Test D — aucun ALLOW fabriqué: Un nouveau nœud DAG ne doit pas valoir ALLOW par défaut."""
    node = DAGNode(task_id="t1", title="test", action_type="coding")
    assert node.policy_decision == "UNTESTED"
    assert node.policy_decision != "ALLOW"


@pytest.mark.asyncio
async def test_mission_allowed_flow(dummy_provider):
    """Test A — mission autorisée : Policy ALLOW, Budget ALLOW, ExecutionDecisionEngine appelé et consommé."""
    master = EzzioMaster(provider=dummy_provider)

    mock_decision = ExecutionDecision(
        execution_type="MODEL",
        target_id="qwen3-coder:30b",
        provider="ollama",
        is_local=True,
        score=95.0,
        rationale="Local sovereign model preferred",
    )

    with patch.object(master.harness.policy_guard, "evaluate_intent", return_value=(True, "Allowed")):
        with patch.object(master.harness.governor, "evaluate_and_record", return_value={"decision": "ALLOW", "reason": "OK"}):
            with patch.object(master.execution_engine, "evaluate_and_decide", return_value=mock_decision) as mock_decide:
                res = await master.orchestrate_multi_agent_mission(
                    mission_prompt="Audite et répare le module de calcul",
                    subtask_specs=[
                        {
                            "task_id": "sub1",
                            "role": "coding",
                            "prompt": "Fix bug in module",
                        }
                    ]
                )

                assert mock_decide.called
                dag = res.get("dag")
                assert dag is not None
                node = dag["nodes"]["sub1"]
                assert node["policy_decision"] == "ALLOW"
                assert node["provider"] == "ollama"
                assert node["agent_id"] == "qwen3-coder:30b"


@pytest.mark.asyncio
async def test_mission_policy_deny(dummy_provider):
    """Test B — Policy DENY: Si Policy=DENY, le nœud échoue immédiatement sans ExecutionDecisionEngine ni Provider."""
    master = EzzioMaster(provider=dummy_provider)

    with patch.object(master.harness.policy_guard, "evaluate_intent", return_value=(False, "Forbidden system command")):
        with patch.object(master.harness.governor, "evaluate_and_record") as mock_gov:
            with patch.object(master.execution_engine, "evaluate_and_decide") as mock_decide:
                res = await master.orchestrate_multi_agent_mission(
                    mission_prompt="Opération interdite",
                    subtask_specs=[
                        {
                            "task_id": "sub1",
                            "role": "forbidden_action",
                            "prompt": "Execute rm -rf",
                        }
                    ]
                )

                assert not mock_decide.called
                dag = res.get("dag")
                assert dag is not None
                node = dag["nodes"]["sub1"]
                assert node["policy_decision"] == "DENY"
                assert node["status"] == DAGExecutionStatus.FAILED.value


@pytest.mark.asyncio
async def test_mission_budget_deny(dummy_provider):
    """Test C — Budget DENY: Si Policy=ALLOW mais Budget=DENY, ExecutionDecisionEngine et Provider ne sont pas appelés."""
    master = EzzioMaster(provider=dummy_provider)

    with patch.object(master.harness.policy_guard, "evaluate_intent", return_value=(True, "Allowed")):
        with patch.object(master.harness.governor, "evaluate_and_record", return_value={"decision": "DENY", "reason": "Token budget exhausted"}):
            with patch.object(master.execution_engine, "evaluate_and_decide") as mock_decide:
                res = await master.orchestrate_multi_agent_mission(
                    mission_prompt="Exécution volumineuse",
                    subtask_specs=[
                        {
                            "task_id": "sub1",
                            "role": "coding",
                            "prompt": "Heavy task",
                        }
                    ]
                )

                assert not mock_decide.called
                dag = res.get("dag")
                assert dag is not None
                node = dag["nodes"]["sub1"]
                assert node["policy_decision"] == "DENY"
                assert node["status"] == DAGExecutionStatus.FAILED.value


@pytest.mark.asyncio
async def test_mission_decision_effectively_consumed(dummy_provider):
    """Test E — décision effectivement consommée: Vérifier que les attributs du DAGNode reflètent la décision d'exécution."""
    master = EzzioMaster(provider=dummy_provider)

    mock_decision_worker = ExecutionDecision(
        execution_type="WORKER",
        target_id="hermes_worker",
        provider="hermes",
        is_local=True,
        score=99.0,
        rationale="Hermes worker selected",
    )

    with patch.object(master.harness.policy_guard, "evaluate_intent", return_value=(True, "OK")):
        with patch.object(master.harness.governor, "evaluate_and_record", return_value={"decision": "ALLOW", "reason": "OK"}):
            with patch.object(master.execution_engine, "evaluate_and_decide", return_value=mock_decision_worker):
                res = await master.orchestrate_multi_agent_mission(
                    mission_prompt="Mission avec worker",
                    subtask_specs=[
                        {
                            "task_id": "sub_w",
                            "role": "forensic",
                            "prompt": "Deep audit",
                        }
                    ]
                )

                dag = res.get("dag")
                assert dag is not None
                node = dag["nodes"]["sub_w"]
                assert node["provider"] == "hermes"
                assert node["agent_id"] == "hermes_worker"
                assert node["policy_decision"] == "ALLOW"
