"""
tests/test_v9_2_platform.py — Tests de certification de la plateforme souveraine E-ZZIO V9.2.
Valide le moteur DAG, le registre dynamique d'agents, la traçabilité des artefacts,
le visualiseur de diff HITL V2, et la résilience des sondes providers.
"""
import asyncio
from pathlib import Path
import pytest

from core.orchestration.dag import (
    TaskDAG,
    DAGNode,
    DAGExecutionStatus,
    CycleDetectedError,
    DependencyNotMetError,
)
from core.orchestration.engine import DAGOrchestrator
from core.agents.registry import AgentRegistry, AgentDescriptor, AgentStatus, agent_registry
from core.artifacts.provenance import ArtifactProvenanceEngine, ArtifactSeal
from core.governance.diff_viewer import HITLDiffViewer
from core.cognitive_router import ModelRouter
from core.security.audit_ledger import AuditLedger


# 1. Tests Moteur DAG
def test_dag_topological_order_and_cycle_detection():
    dag = TaskDAG(name="test_order")
    n1 = dag.add_node("task_1", "Step 1", "action_read")
    n2 = dag.add_node("task_2", "Step 2", "action_process", dependencies=["task_1"])
    n3 = dag.add_node("task_3", "Step 3", "action_write", dependencies=["task_2"])

    order = dag.get_topological_order()
    assert order == ["task_1", "task_2", "task_3"]

    # Test détection de cycle
    dag_cycle = TaskDAG(name="test_cycle")
    dag_cycle.add_node("a", "A", "act")
    dag_cycle.add_node("b", "B", "act", dependencies=["a"])
    with pytest.raises(CycleDetectedError):
        dag_cycle.add_node("c", "C", "act", dependencies=["b"])
        # Forcer cycle
        dag_cycle.nodes["a"].dependencies.append("c")
        dag_cycle.validate()


@pytest.mark.asyncio
async def test_dag_orchestrator_execution_and_cascade_skip(tmp_path: Path):
    ledger = AuditLedger(db_path=str(tmp_path / "dag_audit.db"))
    orchestrator = DAGOrchestrator(audit_ledger=ledger)

    async def success_handler(node: DAGNode):
        return {"output": f"done_{node.task_id}"}

    async def failing_handler(node: DAGNode):
        raise RuntimeError("Fatal node failure")

    orchestrator.register_handler("ok", success_handler)
    orchestrator.register_handler("fail", failing_handler)

    dag = TaskDAG(name="test_cascade")
    dag.add_node("step_1", "Step 1", "fail", max_retries=0)
    dag.add_node("step_2", "Step 2", "ok", dependencies=["step_1"])

    result = await orchestrator.execute_dag(dag)

    assert result["is_failed"] is True
    assert dag.nodes["step_1"].status == DAGExecutionStatus.FAILED
    assert dag.nodes["step_2"].status == DAGExecutionStatus.SKIPPED


# 2. Tests Registre Dynamique d'Agents
def test_agent_registry_lifecycle_and_heartbeat():
    reg = AgentRegistry()
    assert len(reg.list_agents()) >= 5

    coder = reg.get_agent("coder_worker")
    assert coder is not None
    assert coder.status == AgentStatus.IDLE

    # Transition d'état
    reg.update_status("coder_worker", AgentStatus.BUSY, current_action="Refactoring DAG engine", progress=75)
    assert coder.status == AgentStatus.BUSY
    assert coder.current_action == "Refactoring DAG engine"
    assert coder.progress == 75

    # Heartbeat
    old_hb = coder.last_heartbeat
    reg.heartbeat("coder_worker")
    assert coder.last_heartbeat >= old_hb


# 3. Tests Moteur de Provenance d'Artefacts
def test_artifact_provenance_sealing_and_tamper_detection(tmp_path: Path):
    ledger = AuditLedger(db_path=str(tmp_path / "art_audit.db"))
    engine = ArtifactProvenanceEngine(db_path=str(tmp_path / "art_prov.db"), audit_ledger=ledger)

    # Créer un fichier artefact
    test_file = tmp_path / "model_output.txt"
    test_file.write_text("Sovereign Model Output Content V9.2", encoding="utf-8")

    seal = engine.seal_artifact(
        file_path=test_file,
        task_id="tsk_test_001",
        agent_id="coder_worker",
        action_type="CODE_SYNTHESIS",
        policy_decision="ALLOW",
        correlation_id="corr_999",
    )

    assert seal.sha256 is not None
    assert seal.size_bytes > 0

    # Vérification d'intégrité
    check = engine.verify_artifact(seal.artifact_id)
    assert check["verified"] is True

    # Altération délibérée (Tamper detection)
    test_file.write_text("Tampered corrupted content!", encoding="utf-8")
    check_tampered = engine.verify_artifact(seal.artifact_id)
    assert check_tampered["verified"] is False
    assert "Tamper detected" in check_tampered["error"]


# 4. Tests HITL Diff Viewer V2
def test_hitl_diff_viewer_unified_diff():
    diff_res = HITLDiffViewer.generate_text_diff(
        original_text="def compute():\n    return 42\n",
        new_text="def compute():\n    return 100\n",
        from_file="old.py",
        to_file="new.py",
    )
    assert diff_res.is_identical is False
    assert diff_res.lines_added == 1
    assert diff_res.lines_removed == 1
    assert "-    return 42" in diff_res.diff_unified
    assert "+    return 100" in diff_res.diff_unified


# 5. Tests Provider Health Probes
@pytest.mark.asyncio
async def test_provider_health_probe_resilience():
    router = ModelRouter(ollama_url="http://127.0.0.1:11434")
    health = await router.probe_ollama()
    assert "online" in health
    assert "latency_ms" in health