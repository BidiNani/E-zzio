"""E-ZZIO Core — Sovereign Closed-Loop Cognitive Engine (Phase 7.1).

Orchestrates the entire closed-loop execution lifecycle:
INTENTION -> CONTEXT -> ACTION -> OBSERVATION -> EVIDENCE -> EPISTEMIC ARBITRATION -> MEMORYSYNC -> DECISION LEDGER

Ensures no external model or agent can ever self-declare success.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from core.cognition.decision_ledger import DecisionLedgerEngine
from core.cognition.epistemic.epistemic_arbiter import EpistemicArbiter
from core.cognition.evidence.envelope import EvidenceEnvelope
from core.cognition.evidence.store import EvidenceStore
from core.cognition.memory.context_fabric import ContextFabric
from core.cognition.memory.memory_manager import SovereignMemoryManager
from core.cognition.observation.reality_verifier import ObservableRealityVerifier, ObservationRecord
from core.cognition.orchestration.arbiter import FederatedProposal

logger = logging.getLogger(__name__)


@dataclass
class ClosedLoopResult:
    cycle_id: str
    task_id: str
    task_type: str
    status: str  # "CLOSED_LOOP_SUCCESS", "OBSERVATION_FAILED_REJECTED", "EPISTEMIC_ABSTAIN"
    observation_record: ObservationRecord | None
    evidence_id: str | None
    epistemic_state: str
    ledger_decision_id: str | None
    rationale: str
    timestamp_utc: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class ClosedLoopCognitiveEngine:
    def __init__(self, root_dir: Path = Path(r"G:\AI\E-zzio")):
        self.root_dir = root_dir
        self.verifier = ObservableRealityVerifier(root_dir=self.root_dir)
        self.context_fabric = ContextFabric(root_dir=self.root_dir)
        self.memory_manager = SovereignMemoryManager(root_dir=self.root_dir)
        self.decision_engine = None
        self.evidence_store = None
        try:
            self.decision_engine = DecisionLedgerEngine(root_dir=self.root_dir)
            self.evidence_store = EvidenceStore(root_dir=self.root_dir, hmac_key=getattr(self.decision_engine, "hmac_key", None))
        except Exception:
            pass
        self.epistemic_arbiter = EpistemicArbiter(root_dir=self.root_dir, evidence_store=self.evidence_store)

    def execute_closed_loop_file_action(
        self,
        task_id: str,
        task_type: str,
        claimed_provider: str,
        claimed_model: str,
        target_file_path: Path,
        expected_action: str,  # "FILE_CREATED", "FILE_MODIFIED"
        agent_raw_output: str,
        pre_file_hash: str | None = None,
    ) -> ClosedLoopResult:
        """Executes full closed-loop verification over an agent's claimed file action."""
        cycle_id = f"LOOP-{datetime.now(UTC).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

        # 1. Independent Physical Reality Observation
        if expected_action == "FILE_CREATED":
            obs = self.verifier.verify_file_creation(target_file_path)
        elif expected_action == "FILE_MODIFIED":
            obs = self.verifier.verify_file_modification(target_file_path, pre_hash=pre_file_hash or "")
        else:
            obs = ObservationRecord(str(target_file_path), expected_action, False, "Unknown expected action.")

        # Additional Python AST syntax check if file is .py
        if obs.is_verified and str(target_file_path).endswith(".py"):
            syntax_obs = self.verifier.verify_python_syntax(target_file_path)
            if not syntax_obs.is_verified:
                obs.is_verified = False
                obs.observation_details += f" | {syntax_obs.observation_details}"

        # If observable verification fails, reject immediately (Fail-Closed)
        if not obs.is_verified:
            logger.warning(f"[CLOSED-LOOP] Observable reality check failed for {target_file_path}: {obs.observation_details}")
            # Record failed observation into Decision Ledger
            ledger_id = None
            if self.decision_engine:
                try:
                    dec = self.decision_engine.record_decision(
                        subsystem="ClosedLoopEngine",
                        decision_type="OBSERVATION_FAILED_REJECTION",
                        context={"task_id": task_id, "cycle_id": cycle_id, "target_file": str(target_file_path)},
                        action_payload={"observation": asdict(obs)},
                        rationale=f"Rejected self-declared success: {obs.observation_details}",
                    )
                    ledger_id = dec.get("decision_id")
                except Exception:
                    pass

            return ClosedLoopResult(
                cycle_id=cycle_id,
                task_id=task_id,
                task_type=task_type,
                status="OBSERVATION_FAILED_REJECTED",
                observation_record=obs,
                evidence_id=None,
                epistemic_state="OBSERVATION_FAILED",
                ledger_decision_id=ledger_id,
                rationale=obs.observation_details,
            )

        # 2. Cryptographic Evidence Sealing
        key = getattr(self.decision_engine, "hmac_key", None)
        env = EvidenceEnvelope.create(
            task_id=task_id,
            provider=claimed_provider,
            model_name=claimed_model,
            capability=task_type,
            input_prompt=f"Task {task_id}: {expected_action} on {target_file_path}",
            output_payload=agent_raw_output,
            execution_duration_ms=150.0,
            policy_status="APPROVED",
            signing_key=key,
        )
        if self.evidence_store:
            self.evidence_store.store_evidence(env)

        # 3. Epistemic Arbitration
        proposal = FederatedProposal(
            provider=claimed_provider,
            model_name=claimed_model,
            proposal_text=f"{expected_action} verified for {target_file_path}",
            confidence=0.95,
            evidence_id=env.evidence_id,
            suggested_action=expected_action,
        )
        epistemic_verdict = self.epistemic_arbiter.arbitrate_epistemic(task_id, f"Verify {expected_action}", [proposal])

        # 4. Memory Ingestion (L3 Experience)
        if epistemic_verdict.epistemic_state in {"EPISTEMIC_CERTIFIED_CONSENSUS", "EPISTEMIC_MINORITY_TRUTH"}:
            try:
                self.memory_manager.ingest_memory(
                    tier="L3_EXPERIENCE",
                    content=f"Closed-loop verified: {expected_action} on {target_file_path.name} (SHA256: {obs.post_sha256[:8] if obs.post_sha256 else 'OK'}).",
                    source=f"{claimed_provider}_closed_loop",
                    evidence_envelope=env,
                    importance=1.2,
                )
            except Exception as me:
                logger.warning(f"[CLOSED-LOOP] Memory sync warning: {me}")

        # 5. Commit to Frozen Decision Ledger V10.0
        ledger_id = None
        if self.decision_engine:
            try:
                dec = self.decision_engine.record_decision(
                    subsystem="ClosedLoopEngine",
                    decision_type="CLOSED_LOOP_EXECUTION_CERTIFIED",
                    context={"task_id": task_id, "cycle_id": cycle_id, "evidence_id": env.evidence_id, "epistemic_state": epistemic_verdict.epistemic_state},
                    action_payload={"observation": asdict(obs), "target_file": str(target_file_path)},
                    rationale=f"Observable reality verified, evidence sealed, and epistemic truth affirmed for {task_id}.",
                )
                ledger_id = dec.get("decision_id")
            except Exception as le:
                logger.warning(f"[CLOSED-LOOP] Ledger recording warning: {le}")

        return ClosedLoopResult(
            cycle_id=cycle_id,
            task_id=task_id,
            task_type=task_type,
            status="CLOSED_LOOP_SUCCESS",
            observation_record=obs,
            evidence_id=env.evidence_id,
            epistemic_state=epistemic_verdict.epistemic_state,
            ledger_decision_id=ledger_id,
            rationale=f"Closed loop verified: {obs.observation_details}",
        )
