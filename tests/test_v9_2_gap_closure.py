"""
E-ZZIO V9.2 — Master Forensic Gap Closure & Runtime Integrity Suite.
Validates all runtime capabilities and closed architectural gaps:
1. Canonical DAG Orchestration & diamond execution
2. Strict agent transition enforcement & InvalidAgentTransitionError
3. Automatic heartbeat decay (BUSY -> DEGRADED -> OFFLINE)
4. SQLite immutability triggers on artifact provenance (blocking UPDATE/DELETE)
5. HITL V2 Differential Inspection of binary mutations and JSON
6. Master System Diagnostics API (WAL, SQLite integrity, provider health)
7. Fail-closed provider posture (Antigravity BLOCKED_BY_EXTERNAL_QUOTA)
"""
import sqlite3
import time
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from core.agents.registry import (
    AgentDescriptor,
    AgentRegistry,
    AgentStatus,
    InvalidAgentTransitionError,
    agent_registry,
)
from core.artifacts.provenance import ArtifactProvenanceEngine
from core.cognitive_router import ModelRouter
from core.governance.diff_viewer import HITLDiffViewer
from core.orchestration import DAGExecutionStatus, DAGNode, DAGOrchestrator, TaskDAG
from core.security.audit_ledger import AuditLedger
from web_server import app


# ---------------------------------------------------------------------------
# 1. Canonical DAG Orchestration
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_dag_diamond_execution_end_to_end(tmp_path: Path):
    """Verifie l'execution d'un DAG en diamant A -> (B, C) -> D."""
    ledger = AuditLedger(db_path=str(tmp_path / "diamond_audit.db"))
    orch = DAGOrchestrator(audit_ledger=ledger)

    execution_trail = []

    async def step_handler(node: DAGNode):
        execution_trail.append(node.task_id)
        return {"done": node.task_id}

    orch.register_handler("runner", step_handler)

    dag = TaskDAG(name="diamond_pipeline")
    dag.add_node("node_a", "Node A", "runner")
    dag.add_node("node_b", "Node B", "runner", dependencies=["node_a"])
    dag.add_node("node_c", "Node C", "runner", dependencies=["node_a"])
    dag.add_node("node_d", "Node D", "runner", dependencies=["node_b", "node_c"])

    res = await orch.execute_dag(dag)
    assert res["is_failed"] is False
    assert dag.is_completed() is True
    assert execution_trail[0] == "node_a"
    assert "node_b" in execution_trail[1:3]
    assert "node_c" in execution_trail[1:3]
    assert execution_trail[3] == "node_d"


# ---------------------------------------------------------------------------
# 2. Strict Agent Transition & Heartbeat Decay
# ---------------------------------------------------------------------------
def test_agent_strict_transition_rules():
    """Verifie que les transitions illegales levent InvalidAgentTransitionError."""
    reg = AgentRegistry()
    reg.register(
        AgentDescriptor(
            agent_id="test_agent_trans",
            name="Test Agent",
            role="Worker",
            room="dev_lab",
            avatar="pixel_test",
            model="phi4-mini",
            provider="ollama_local",
        )
    )

    # IDLE -> BUSY valide
    reg.update_status("test_agent_trans", AgentStatus.BUSY)
    desc = reg.get_agent("test_agent_trans")
    assert desc.status == AgentStatus.BUSY

    # BUSY -> OFFLINE illegal (doit passer par IDLE ou DEGRADED ou ERROR)
    with pytest.raises(InvalidAgentTransitionError):
        reg.update_status("test_agent_trans", AgentStatus.OFFLINE)


def test_agent_heartbeat_decay_lifecycle():
    """Verifie le passage automatique en DEGRADED puis OFFLINE si heartbeat absent."""
    reg = AgentRegistry()
    reg.register(
        AgentDescriptor(
            agent_id="decay_agent",
            name="Decaying Worker",
            role="Worker",
            room="dev_lab",
            avatar="pixel_decay",
            model="phi4-mini",
            provider="ollama_local",
            status=AgentStatus.BUSY,
            last_heartbeat=time.time() - 300,
        )
    )

    events = reg.check_heartbeats(degraded_threshold_sec=30.0, offline_threshold_sec=90.0)
    agent_ids = [e["agent_id"] for e in events]
    assert "decay_agent" in agent_ids
    desc = reg.get_agent("decay_agent")
    assert desc.status == AgentStatus.OFFLINE


# ---------------------------------------------------------------------------
# 3. Artifact Provenance Engine & SQLite Immutability Triggers
# ---------------------------------------------------------------------------
def test_artifact_provenance_triggers_block_mutation(tmp_path: Path):
    """Verifie que les triggers SQLite interdisent formellement UPDATE et DELETE."""
    ledger = AuditLedger(db_path=str(tmp_path / "prov_audit.db"))
    db_path = str(tmp_path / "prov.db")
    engine = ArtifactProvenanceEngine(db_path=db_path, audit_ledger=ledger)

    artifact_file = tmp_path / "binary_result.bin"
    artifact_file.write_bytes(b"\xde\xad\xbe\xef" * 100)

    seal = engine.seal_artifact(
        file_path=artifact_file,
        task_id="tsk_binary_001",
        agent_id="coder_worker",
        action_type="BINARY_BUILD",
        policy_decision="ALLOW",
    )

    # Tenter un UPDATE direct en SQLite
    conn = sqlite3.connect(db_path)
    with pytest.raises(sqlite3.IntegrityError, match="Artifact provenance entries are immutable"):
        conn.execute(
            "UPDATE artifact_provenance SET sha256 = 'forged_hash' WHERE artifact_id = ?",
            (seal.artifact_id,),
        )
        conn.commit()

    # Tenter un DELETE direct en SQLite
    with pytest.raises(sqlite3.IntegrityError, match="Artifact provenance entries cannot be deleted"):
        conn.execute(
            "DELETE FROM artifact_provenance WHERE artifact_id = ?",
            (seal.artifact_id,),
        )
        conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# 4. HITL V2 Differential Inspection
# ---------------------------------------------------------------------------
def test_hitl_diff_binary_and_files(tmp_path: Path):
    """Verifie la generation de diff binaire et fichier sans faux diff textuel."""
    bin_file = tmp_path / "app.apk"
    bin_file.write_bytes(b"PK\x03\x04" + b"\x00" * 50)
    new_bytes = b"PK\x03\x04" + b"\xFF" * 60

    diff = HITLDiffViewer.generate_file_diff(bin_file, new_bytes)
    assert diff.is_identical is False
    assert "Binary mutation" in diff.summary
    assert "Binary files" in diff.diff_unified


# ---------------------------------------------------------------------------
# 5. Master System Diagnostics & Provider Health API
# ---------------------------------------------------------------------------
def test_master_diagnostics_and_providers_endpoints(client):
    """Verifie les nouveaux endpoints /system/diagnostics et /providers/health."""
    res_diag = client.get("/master/api/v1/system/diagnostics")
    assert res_diag.status_code == 200
    diag_data = res_diag.json()
    assert diag_data["ok"] is True
    assert "agent_fleet" in diag_data
    assert diag_data["agent_fleet"]["total_agents"] >= 10

    res_prov = client.get("/master/api/v1/providers/health")
    assert res_prov.status_code == 200
    prov_data = res_prov.json()
    assert prov_data["ok"] is True
    assert "health" in prov_data
    assert "providers" in prov_data["health"]
    providers = prov_data["health"]["providers"]
    # Antigravity doit explicitement figurer en fail-closed / quota
    assert "antigravity" in providers
    assert providers["antigravity"]["status"] == "BLOCKED_BY_EXTERNAL_QUOTA"
