"""
tests/test_project_completion_e2e.py — Validation E2E A4 : Completion réelle d'un projet technique.
Démontre qu'E-ZZIO peut :
1. Décomposer et exécuter un pipeline DAG (inspect -> diagnose -> modify -> test -> validate)
2. Effectuer des modifications de fichiers réelles sur disque et exécuter des tests réels
3. Gérer la récupération d'échec borné (bounded retry & recovery)
4. Survivre à un crash/interruption et reprendre de façon idempotente sans rejouer les étapes validées
5. Produire la preuve structurée finale avec traçabilité AuditLedger cryptographique.
"""
import asyncio
import subprocess
import sys
from pathlib import Path

import pytest

from core.agent.mission_controller import MissionRecord, MissionRegistry, MissionStatus
from core.orchestration.dag import DAGExecutionStatus, TaskDAG
from core.orchestration.engine import DAGOrchestrator
from core.security.audit_ledger import AuditLedger


@pytest.mark.asyncio
async def test_e2e_project_completion_pipeline_and_crash_recovery(tmp_path: Path) -> None:
    # 0. Setup du projet fixture local
    proj_dir = tmp_path / "fixture_calc_project"
    proj_dir.mkdir(parents=True, exist_ok=True)
    tests_dir = proj_dir / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)

    calc_file = proj_dir / "calculator.py"
    test_file = tests_dir / "test_calculator.py"

    # Fichier initial avec un bug intentionnel (soustraction au lieu d'addition)
    calc_file.write_text(
        "def add(a: int, b: int) -> int:\n"
        "    # BUG INTENTIONNEL : '-' au lieu de '+'\n"
        "    return a - b\n",
        encoding="utf-8"
    )

    test_file.write_text(
        "import sys\n"
        "from pathlib import Path\n"
        "sys.path.insert(0, str(Path(__file__).parent.parent))\n"
        "from calculator import add\n\n"
        "def test_add():\n"
        "    assert add(2, 3) == 5\n",
        encoding="utf-8"
    )

    db_path = tmp_path / "missions_a4.db"
    audit_db_path = tmp_path / "audit_a4.db"

    # =========================================================================
    # PHASE 1 : Création et premier lancement de la mission
    # =========================================================================
    registry_v1 = MissionRegistry(db_path=db_path)
    audit_v1 = AuditLedger(db_path=str(audit_db_path), workspace_root=str(tmp_path))
    orchestrator_v1 = DAGOrchestrator(audit_ledger=audit_v1)

    mission_id = "msn_a4_e2e_completion_001"
    record_v1 = MissionRecord(
        mission_id=mission_id,
        goal="Corriger le bug d'addition dans calculator.py et exécuter les tests",
        worker_type="CODER_WORKER",
        status=MissionStatus.RUNNING,
    )

    dag_v1 = TaskDAG(dag_id=f"dag-{mission_id}", name="project_completion_dag")
    dag_v1.add_node("node_inspect", "Inspecter le projet", "action_inspect")
    dag_v1.add_node("node_diagnose", "Diagnostiquer le bug", "action_diagnose", dependencies=["node_inspect"])
    dag_v1.add_node("node_modify", "Corriger le code calculator.py", "action_modify", dependencies=["node_diagnose"])
    dag_v1.add_node("node_test", "Exécuter les tests pytest", "action_test", dependencies=["node_modify"])
    dag_v1.add_node("node_validate", "Valider la complétion et la preuve", "action_validate", dependencies=["node_test"])

    registry_v1.register(record_v1, dag=dag_v1)

    exec_counts = {"inspect": 0, "diagnose": 0, "modify": 0, "test": 0, "validate": 0}

    async def inspect_handler(node):
        exec_counts["inspect"] += 1
        return {"inspect_ok": True, "files": ["calculator.py", "tests/test_calculator.py"]}

    async def diagnose_handler(node):
        exec_counts["diagnose"] += 1
        return {"bug_found": True, "target": "calculator.py", "reason": "a - b inside add"}

    async def modify_handler(node):
        exec_counts["modify"] += 1
        # Modification réelle sur disque du fichier calculator.py
        calc_file.write_text(
            "def add(a: int, b: int) -> int:\n"
            "    # BUG CORRIGÉ : '+' au lieu de '-'\n"
            "    return a + b\n",
            encoding="utf-8"
        )
        return {"changed_files": ["calculator.py"], "applied_fix": "return a + b"}

    # Injections handlers Phase 1 (simulation crash sur node_test)
    test_attempts = 0

    async def test_handler_simulated_crash(node):
        nonlocal test_attempts
        exec_counts["test"] += 1
        test_attempts += 1
        # Simuler un crash/kill du processus au démarrage du nœud de test
        raise RuntimeError("SIMULATED_PROCESS_INTERRUPTION_MID_TEST")

    orchestrator_v1.register_handler("action_inspect", inspect_handler)
    orchestrator_v1.register_handler("action_diagnose", diagnose_handler)
    orchestrator_v1.register_handler("action_modify", modify_handler)
    orchestrator_v1.register_handler("action_test", test_handler_simulated_crash)

    # Exécution partielle V1
    await orchestrator_v1.execute_dag(dag_v1)

    # Vérifications V1 post-crash
    assert dag_v1.nodes["node_inspect"].status == DAGExecutionStatus.COMPLETED
    assert dag_v1.nodes["node_diagnose"].status == DAGExecutionStatus.COMPLETED
    assert dag_v1.nodes["node_modify"].status == DAGExecutionStatus.COMPLETED
    assert calc_file.read_text(encoding="utf-8").find("return a + b") != -1, "La modification réelle n'a pas eu lieu sur disque !"
    assert exec_counts["inspect"] == 1
    assert exec_counts["diagnose"] == 1
    assert exec_counts["modify"] == 1

    registry_v1.checkpoint_dag(mission_id, dag_v1)

    # =========================================================================
    # PHASE 2 : CRASH / RESTART RUNTIME & RESUME IDEMPOTENT
    # =========================================================================
    DAGOrchestrator._instance = None
    registry_v2 = MissionRegistry(db_path=db_path)
    audit_v2 = AuditLedger(db_path=str(audit_db_path), workspace_root=str(tmp_path))
    orchestrator_v2 = DAGOrchestrator(audit_ledger=audit_v2)

    restored_record = registry_v2.get(mission_id)
    assert restored_record is not None

    restored_dag_json = registry_v2.get_dag_checkpoint(mission_id)
    assert restored_dag_json is not None
    restored_dag = TaskDAG.from_dict(restored_dag_json)

    # Handler réel de test exécutant la validation du projet via un sous-processus Python
    async def test_handler_real(node):
        exec_counts["test"] += 1
        code_runner = (
            "import sys; "
            f"sys.path.insert(0, r'{proj_dir}'); "
            "from tests.test_calculator import test_add; "
            "test_add(); "
            "print('TEST_PASSED')"
        )
        cmd = [sys.executable, "-c", code_runner]
        res = subprocess.run(cmd, cwd=str(proj_dir), capture_output=True, text=True, errors="replace")
        if res.returncode != 0 or "TEST_PASSED" not in res.stdout:
            raise RuntimeError(f"Test runner failed: {res.stderr or res.stdout}")
        return {
            "tests_run": 1,
            "tests_passed": 1,
            "exit_code": 0,
            "stdout": res.stdout,
            "recovered": True,
        }

    async def validate_handler(node):
        exec_counts["validate"] += 1
        # Vérification formelle d'intégrité de la complétion
        content = calc_file.read_text(encoding="utf-8")
        assert "return a + b" in content
        return {
            "validated": True,
            "changed_files": ["calculator.py"],
            "tests_run": 1,
            "tests_passed": 1,
        }

    orchestrator_v2.register_handler("action_inspect", inspect_handler)
    orchestrator_v2.register_handler("action_diagnose", diagnose_handler)
    orchestrator_v2.register_handler("action_modify", modify_handler)
    orchestrator_v2.register_handler("action_test", test_handler_real)
    orchestrator_v2.register_handler("action_validate", validate_handler)

    # Réinitialiser node_test et node_validate pour reprise
    restored_dag.nodes["node_test"].status = DAGExecutionStatus.PENDING
    restored_dag.nodes["node_test"].retry_count = 0
    restored_dag.nodes["node_validate"].status = DAGExecutionStatus.PENDING

    # Relancer l'exécution post-crash
    await orchestrator_v2.execute_dag(restored_dag)

    # =========================================================================
    # PHASE 3 : VÉRIFICATION DES PREUVES ET DE L'IDEMPOTENCE
    # =========================================================================
    # 1. Idempotence : Les étapes inspect, diagnose, modify n'ont PAS été ré-exécutées
    assert exec_counts["inspect"] == 1, "node_inspect a été ré-exécuté accidentellement !"
    assert exec_counts["diagnose"] == 1, "node_diagnose a été ré-exécuté accidentellement !"
    assert exec_counts["modify"] == 1, "node_modify a été ré-exécuté accidentellement !"

    # 2. Complétion réelle : node_test et node_validate ont bien été exécutés
    assert exec_counts["test"] >= 2, "node_test aurait dû être repris et exécuté !"
    assert exec_counts["validate"] == 1, "node_validate aurait dû s'exécuter !"

    assert restored_dag.is_completed() is True
    assert restored_dag.nodes["node_inspect"].status == DAGExecutionStatus.COMPLETED
    assert restored_dag.nodes["node_diagnose"].status == DAGExecutionStatus.COMPLETED
    assert restored_dag.nodes["node_modify"].status == DAGExecutionStatus.COMPLETED
    assert restored_dag.nodes["node_test"].status == DAGExecutionStatus.COMPLETED
    assert restored_dag.nodes["node_validate"].status == DAGExecutionStatus.COMPLETED

    restored_record.status = MissionStatus.SUCCEEDED
    registry_v2.update_mission(restored_record, restored_dag)

    # 3. Preuve de complétion structurée (Completion Evidence)
    evidence = restored_record.get_completion_evidence(restored_dag)

    assert evidence["mission_id"] == mission_id
    assert evidence["final_status"] == "SUCCEEDED"
    assert "calculator.py" in evidence["changed_files"]
    assert evidence["tests_run"] >= 1
    assert evidence["tests_passed"] >= 1
    assert evidence["nodes_completed"] == 5
    assert evidence["recovered"] is True

    # 4. Vérification de l'intégrité cryptographique de l'AuditLedger
    is_valid, count, err = audit_v2.verify_chain_integrity()
    assert is_valid is True, f"AuditLedger intégrité invalide: {err}"
    assert count > 0, "AuditLedger est vide !"


@pytest.mark.asyncio
async def test_bounded_retry_failure_recovery_flow(tmp_path: Path) -> None:
    db_path = tmp_path / "retry_test.db"
    registry = MissionRegistry(db_path=db_path)
    audit = AuditLedger(db_path=str(tmp_path / "audit_retry.db"), workspace_root=str(tmp_path))
    orchestrator = DAGOrchestrator(audit_ledger=audit)

    mission_id = "msn_retry_002"
    record = MissionRecord(mission_id=mission_id, goal="Test de retry borné", status=MissionStatus.RUNNING)
    dag = TaskDAG(dag_id=f"dag-{mission_id}", name="retry_dag")
    node = dag.add_node("step_flaky", "Tâche instable", "action_flaky", max_retries=2)

    registry.register(record, dag=dag)

    attempts = 0

    async def flaky_handler(n):
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise ValueError("Échec temporaire simulant un flakiness de réseau/build")
        return {"status": "recovered_on_retry", "attempts": attempts}

    orchestrator.register_handler("action_flaky", flaky_handler)

    await orchestrator.execute_dag(dag)

    assert dag.nodes["step_flaky"].status == DAGExecutionStatus.COMPLETED
    assert attempts == 2
    assert node.retry_count == 1
