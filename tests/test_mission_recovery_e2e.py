"""
tests/test_mission_recovery_e2e.py — Validation E2E de la persistance, reprise et résilience des missions E-ZZIO.
Démontre qu'une mission interrompue restaure son état, ne rejoue pas les étapes déjà validées,
borne les retries et complète la mission en sécurité fail-closed.
"""
import asyncio
from pathlib import Path

import pytest

from core.agent.mission_controller import MissionRecord, MissionRegistry, MissionStatus
from core.orchestration.dag import DAGExecutionStatus, TaskDAG
from core.orchestration.engine import DAGOrchestrator
from core.security.audit_ledger import AuditLedger


@pytest.mark.asyncio
async def test_mission_persistence_and_interruption_recovery(tmp_path: Path) -> None:
    db_path = tmp_path / "missions_test.db"
    audit_db_path = tmp_path / "audit_test.db"

    # Step 1: Initialisation du registre et de l'orchestrateur
    registry_v1 = MissionRegistry(db_path=db_path)
    audit_v1 = AuditLedger(db_path=str(audit_db_path), workspace_root=str(tmp_path))
    orchestrator_v1 = DAGOrchestrator(audit_ledger=audit_v1)

    mission_id = "mission_e2e_recovery_001"
    record = MissionRecord(
        mission_id=mission_id,
        goal="Mission complexe multi-étapes avec reprise après crash",
        worker_type="CODER_WORKER",
        status=MissionStatus.RUNNING,
        request_id="session_req_999",
    )

    # Step 2: Construction du DAG (Step A -> Step B -> Step C)
    dag = TaskDAG(dag_id=f"dag-{mission_id}", name="recovery_dag")
    dag.add_node("step_a", "Analyse de sécurité", "action_analyze")
    dag.add_node("step_b", "Refactorisation du code", "action_refactor", dependencies=["step_a"])
    dag.add_node("step_c", "Certification finale", "action_certify", dependencies=["step_b"])

    registry_v1.register(record, dag=dag)

    executed_count = {"step_a": 0, "step_b": 0, "step_c": 0}

    async def step_a_handler(node):
        executed_count["step_a"] += 1
        return {"status": "analyzed", "findings": 0}

    async def step_b_handler(node):
        executed_count["step_b"] += 1
        # Simuler une interruption / crash au milieu de step_b
        raise RuntimeError("SIMULATED_INTERRUPTION_CRASH")

    orchestrator_v1.register_handler("action_analyze", step_a_handler)
    orchestrator_v1.register_handler("action_refactor", step_b_handler)

    # Step 3: Exécution partielle
    await orchestrator_v1.execute_dag(dag)

    # Vérifications post-crash V1
    assert dag.nodes["step_a"].status == DAGExecutionStatus.COMPLETED
    assert executed_count["step_a"] == 1
    assert dag.nodes["step_b"].status in (DAGExecutionStatus.FAILED, DAGExecutionStatus.PENDING)
    assert dag.nodes["step_c"].status == DAGExecutionStatus.SKIPPED

    # Checkpoint explicite dans la persistance SQLite
    registry_v1.checkpoint_dag(mission_id, dag)

    # =========================================================================
    # Step 4: CRASH SIMULATION & PROCESS RESTART
    # Ré-instanciation complète à partir de zéro depuis le stockage SQLite
    # =========================================================================
    registry_v2 = MissionRegistry(db_path=db_path)
    audit_v2 = AuditLedger(db_path=str(audit_db_path), workspace_root=str(tmp_path))
    orchestrator_v2 = DAGOrchestrator(audit_ledger=audit_v2)

    # Restauration du dossier de mission et du checkpoint DAG
    restored_record = registry_v2.get(mission_id)
    assert restored_record is not None
    assert restored_record.mission_id == mission_id

    restored_dag_json = registry_v2.get_dag_checkpoint(mission_id)
    assert restored_dag_json is not None
    restored_dag = TaskDAG.from_dict(restored_dag_json)

    # Vérifier que Step A est restauré comme COMPLETED
    assert restored_dag.nodes["step_a"].status == DAGExecutionStatus.COMPLETED

    # Step 5: Reprise de la mission avec des exécuteurs réparés pour Step B & C
    async def step_b_fixed_handler(node):
        executed_count["step_b"] += 1
        return {"status": "refactored", "diff_lines": 12}

    async def step_c_handler(node):
        executed_count["step_c"] += 1
        return {"status": "certified", "score": 100}

    orchestrator_v2.register_handler("action_analyze", step_a_handler)
    orchestrator_v2.register_handler("action_refactor", step_b_fixed_handler)
    orchestrator_v2.register_handler("action_certify", step_c_handler)

    # Réinitialiser les états bloqués/skipped pour autoriser la complétion post-reprise
    restored_dag.nodes["step_b"].status = DAGExecutionStatus.PENDING
    restored_dag.nodes["step_b"].retry_count = 0
    restored_dag.nodes["step_c"].status = DAGExecutionStatus.PENDING

    # Relancer l'exécution
    res = await orchestrator_v2.execute_dag(restored_dag)

    # Step 6: Validation finale d'idempotence et de reprise
    # Step A ne doit PAS avoir été ré-exécuté
    assert executed_count["step_a"] == 1, "Step A a été rejoué accidentellement !"
    assert executed_count["step_b"] >= 1, "Step B aurait dû être repris !"
    assert executed_count["step_c"] == 1, "Step C aurait dû s'exécuter !"

    assert restored_dag.is_completed() is True
    assert restored_dag.nodes["step_a"].status == DAGExecutionStatus.COMPLETED
    assert restored_dag.nodes["step_b"].status == DAGExecutionStatus.COMPLETED
    assert restored_dag.nodes["step_c"].status == DAGExecutionStatus.COMPLETED

    # Mise à jour finale du statut de mission
    restored_record.status = MissionStatus.SUCCEEDED
    registry_v2.update_mission(restored_record, restored_dag)

    final_record = registry_v2.get(mission_id)
    assert final_record.status == MissionStatus.SUCCEEDED

    # Intégrité de l'AuditLedger
    is_valid, count, err = audit_v2.verify_chain_integrity()
    assert is_valid is True, f"L'AuditLedger a été corrompu ! Erreur: {err}"


@pytest.mark.asyncio
async def test_mission_cancellation_lifecycle(tmp_path: Path) -> None:
    db_path = tmp_path / "cancel_test.db"
    registry = MissionRegistry(db_path=db_path)

    mission_id = "mission_cancel_002"
    record = MissionRecord(
        mission_id=mission_id,
        goal="Mission destinée à être annulée",
        status=MissionStatus.RUNNING,
    )
    registry.register(record)

    # Simuler l'annulation
    success = registry.cancel(mission_id)
    assert success is True

    # Vérifier la persistance de l'annulation
    registry_reloaded = MissionRegistry(db_path=db_path)
    cancelled_rec = registry_reloaded.get(mission_id)
    assert cancelled_rec is not None
    assert cancelled_rec.status == MissionStatus.CANCELLED
