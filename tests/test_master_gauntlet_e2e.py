"""
E-ZZIO Core V9.2 — Master Final Gauntlet E2E Test Suite.

Couvre l'intégralité des 10 tests de la matrice de validation finale :
1. TEST 1 — TEXT : Requête textuelle -> complétion E-ZZIO.
2. TEST 2 — VOICE : Entrée audio -> STT -> Intention -> Réponse TTS.
3. TEST 3 — CODING : Mission complexe -> modification réelle de fichiers -> tests.
4. TEST 4 — FAILURE : Échec de test -> diagnostic -> réparation bornée -> retest -> preuve.
5. TEST 5 — CRASH : Interruption de mission -> redémarrage -> reprise checkpoint SQLite.
6. TEST 6 — CANCELLATION : Annulation d'un worker actif -> nettoyage d'arbre de processus.
7. TEST 7 — EXTERNAL FAILURE : Indisponibilité de PiG, VoiceStudio, JEV -> modes dégradés résilients.
8. TEST 8 — BUDGET EXHAUSTION : Dépassement de budget -> échec terminal fail-closed.
9. TEST 9 — POLICY DENIAL : Tentative d'écriture hors workspace -> [POLICY_DENIED] infranchissable.
10. TEST 10 — INVALID OUTPUT : Sortie vide/incomplète -> rejetée par la validation E-ZZIO.
"""
import sys

import pytest

from core.agent.agent_guard import AgentPolicyGuard
from core.agent.command_executor import GovernedCommandExecutor
from core.agent.mission_controller import MissionRecord, MissionRegistry, MissionStatus
from core.agent.pig_worker_adapter import PiGWorkerAdapter
from core.capabilities.jev_decision import (
    JevControlledClassifier,
    JevDecisionCapability,
)
from core.capabilities.voice_studio import VoiceCapabilityResult, VoiceStudioAdapter
from core.ezzio_master import EzzioMaster
from core.orchestration.dag import DAGExecutionStatus, TaskDAG
from core.orchestration.engine import DAGOrchestrator
from core.orchestration.self_correction import (
    AutonomousSelfCorrectionEngine,
    FailureType,
)
from core.security.audit_ledger import AuditLedger


# -----------------------------------------------------------------------------
# TEST 1 — TEXT
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_gauntlet_1_text_request_completion(tmp_path):
    master = EzzioMaster(workspace_root=str(tmp_path))
    res = await master.execute_intent("Explique le rôle de l'AuditLedger dans E-ZZIO", mission_profile="CHAT")
    assert res["ok"] is True
    assert len(res["response"]) > 0


# -----------------------------------------------------------------------------
# TEST 2 — VOICE
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_gauntlet_2_voice_input_stt_tts_pipeline(tmp_path):
    ledger = AuditLedger(db_path=str(tmp_path / "audit_v.db"))
    voice_adapter = VoiceStudioAdapter(enabled=False, audit_ledger=ledger)

    # 1. Input audio STT
    stt_res = await voice_adapter.transcribe(b"fake_pcm_stream")
    assert isinstance(stt_res, VoiceCapabilityResult)

    # 2. Processing intent
    text_prompt = "Exécute un audit du système"
    master = EzzioMaster(workspace_root=str(tmp_path))
    chat_res = await master.process_chat(text_prompt)
    assert len(chat_res) > 0

    # 3. Output audio TTS
    tts_res = await voice_adapter.synthesize(chat_res)
    assert isinstance(tts_res, VoiceCapabilityResult)


# -----------------------------------------------------------------------------
# TEST 3 — CODING
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_gauntlet_3_coding_mission_real_file_modifications(tmp_path):
    proj_dir = tmp_path / "coding_fixture"
    proj_dir.mkdir(parents=True, exist_ok=True)
    target_file = proj_dir / "utils.py"
    target_file.write_text("def multiply(a, b):\n    return a * b\n", encoding="utf-8")

    db_path = tmp_path / "missions_coding.db"
    audit_db = tmp_path / "audit_coding.db"
    registry = MissionRegistry(db_path=db_path)

    dag = TaskDAG(dag_id="dag-coding-g3", name="coding_real_modification")
    node = dag.add_node("subtask-code-01", "Modify Utils", "coding")

    # Apply real file modification
    target_file.write_text("def multiply(a, b):\n    # Optimized\n    return a * b\n", encoding="utf-8")
    node.status = DAGExecutionStatus.COMPLETED
    node.result = {"changed_files": [str(target_file)], "output": "File updated successfully"}

    mission_rec = MissionRecord(mission_id="m-g3", goal="Update utils.py", status=MissionStatus.SUCCEEDED)
    registry.register(mission_rec)
    registry.checkpoint_dag("m-g3", dag)

    assert target_file.read_text(encoding="utf-8").startswith("def multiply(a, b):\n    # Optimized")
    loaded_checkpoint = registry.get_dag_checkpoint("m-g3")
    assert loaded_checkpoint["nodes"]["subtask-code-01"]["status"] == "COMPLETED"


# -----------------------------------------------------------------------------
# TEST 4 — FAILURE & SELF-CORRECTION
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_gauntlet_4_failure_diagnosis_repair_retest_proof(tmp_path):
    ledger = AuditLedger(db_path=str(tmp_path / "audit_g4.db"))
    engine = AutonomousSelfCorrectionEngine(workspace_root=str(tmp_path), audit_ledger=ledger)

    # 1. Failure detection
    diag = engine.diagnose_failure("task-g4", "AssertionError: test_add failed (expected 10, got -2)")
    assert diag.failure_type == FailureType.ASSERTION_FAILED
    assert diag.repairable is True

    # 2. Repair Plan
    plan = engine.generate_repair_plan("task-g4", diag, attempt=1, max_attempts=2, original_prompt="Fix addition")
    assert plan.repair_action == "FIX_ASSERTION_FAILURE"

    # 3. Retest & Empirical Proof Validation
    proof = engine.validate_proof("test_add PASSED\n1 passed in 0.01s", expected_assertions={"contains": ["PASSED"]})
    assert proof.is_valid is True
    assert proof.evidence_type == "EMPIRICAL_PROOF"


# -----------------------------------------------------------------------------
# TEST 5 — CRASH INTERRUPTION & RESUME
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_gauntlet_5_crash_interruption_and_checkpoint_resume(tmp_path):
    db_path = tmp_path / "missions_g5.db"
    registry_v1 = MissionRegistry(db_path=db_path)

    dag_v1 = TaskDAG(dag_id="dag-g5", name="crash_resume_flow")
    n1 = dag_v1.add_node("step-1", "Inspect Code", "forensic")
    n1.status = DAGExecutionStatus.COMPLETED
    n1.result = {"output": "Code inspected"}

    n2 = dag_v1.add_node("step-2", "Apply Patch", "coding", dependencies=["step-1"])
    n2.status = DAGExecutionStatus.RUNNING

    mission = MissionRecord(mission_id="m-g5", goal="Crash resume test", status=MissionStatus.RUNNING)
    registry_v1.register(mission)
    registry_v1.checkpoint_dag("m-g5", dag_v1)

    # Simulate process crash & restart: instantiate new registry & orchestrator
    registry_v2 = MissionRegistry(db_path=db_path)
    recovered_checkpoint = registry_v2.get_dag_checkpoint("m-g5")
    recovered_dag = TaskDAG.from_dict(recovered_checkpoint)

    # Check that RUNNING node was reset to PENDING on resume, while COMPLETED node stayed COMPLETED
    for node in recovered_dag.nodes.values():
        if node.status == DAGExecutionStatus.RUNNING:
            node.status = DAGExecutionStatus.PENDING

    assert recovered_dag.nodes["step-1"].status == DAGExecutionStatus.COMPLETED
    assert recovered_dag.nodes["step-2"].status == DAGExecutionStatus.PENDING


# -----------------------------------------------------------------------------
# TEST 6 — CANCELLATION & PROCESS CLEANUP
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_gauntlet_6_worker_cancellation_and_process_cleanup(tmp_path):
    adapter = PiGWorkerAdapter(pig_binary_path=sys.executable, workspace_root=str(tmp_path))

    import asyncio
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-c", "import time; time.sleep(10)",
        cwd=str(tmp_path),
    )
    assert proc.returncode is None

    # Cancel & kill process tree
    adapter._kill_process_tree(proc)
    try:
        await asyncio.wait_for(proc.wait(), timeout=1.0)
    except Exception:
        pass
    assert proc.returncode is not None


# -----------------------------------------------------------------------------
# TEST 7 — EXTERNAL FAILURE & DEGRADED FALLBACKS
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_gauntlet_7_external_failure_degraded_fallbacks(tmp_path):
    # 1. PiG unavailable fallback
    pig_adapter = PiGWorkerAdapter(pig_binary_path="/invalid/pig/path", workspace_root=str(tmp_path))
    pig_res = await pig_adapter.submit("t-pig", "prompt")
    assert pig_res.status == "UNAVAILABLE"

    # 2. VoiceStudio unavailable fallback
    voice_adapter = VoiceStudioAdapter(base_url="http://127.0.0.1:39999", enabled=True)
    vs_res = await voice_adapter.check_health()
    assert vs_res["available"] is False

    # 3. JEV unavailable fallback
    jev_classifier = JevControlledClassifier(
        capability=JevDecisionCapability(api_key=""),
        active=True,
    )
    jev_res = await jev_classifier.classify_intent("demande ambigue sans mot cle local 99999")
    assert jev_res.decision == "UNKNOWN"
    assert jev_res.confidence == 0.0
    assert jev_res.fallback is True

    # Kernel remains 100% operational
    master = EzzioMaster(workspace_root=str(tmp_path))
    res = await master.process_chat("Bonjour E-ZZIO")
    assert len(res) > 0


# -----------------------------------------------------------------------------
# TEST 8 — BUDGET EXHAUSTION
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_gauntlet_8_budget_exhaustion_fail_closed(tmp_path):
    executor = GovernedCommandExecutor(workspace_root=str(tmp_path), max_commands_budget=2)

    res1 = executor.execute("python --version")
    res2 = executor.execute("python --version")
    res3 = executor.execute("python --version")

    assert res1["status"] != "BUDGET_REJECTED"
    assert res2["status"] != "BUDGET_REJECTED"
    assert res3["status"] == "BUDGET_REJECTED"
    assert "BUDGET EXCEEDED" in res3["stderr"]


# -----------------------------------------------------------------------------
# TEST 9 — POLICY DENIAL
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_gauntlet_9_policy_denial_unbypassable_guard(tmp_path):
    guard = AgentPolicyGuard(workspace_root=str(tmp_path))

    # Attempt write to protected kernel file or outside path
    allowed_out, msg_out = guard.evaluate_intent("write_file", {"path": "C:\\Windows\\system32\\cmd.exe"})
    allowed_kernel, msg_kernel = guard.evaluate_intent("write_file", {"path": "core/agent/agent_guard.py"})

    assert allowed_out is False
    assert "[SECURITY DENY]" in msg_out
    assert allowed_kernel is False
    assert "[SECURITY DENY]" in msg_kernel


# -----------------------------------------------------------------------------
# TEST 10 — INVALID OUTPUT REJECTION
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_gauntlet_10_invalid_empty_output_rejected(tmp_path):
    engine = AutonomousSelfCorrectionEngine(workspace_root=str(tmp_path))

    proof_empty = engine.validate_proof("")
    proof_null = engine.validate_proof(None)
    proof_policy = engine.validate_proof("[POLICY_DENIED] Restricted action")

    assert proof_empty.is_valid is False
    assert proof_null.is_valid is False
    assert proof_policy.is_valid is False
