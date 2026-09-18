"""E-ZZIO Core — Federated Cognitive Orchestrator (Phase 6.0).

Coordinates multi-model execution flows (collaborative pipelines, consensus arbitration, agentic verification)
and commits arbitrated decisions to the frozen Decision Ledger V10.0 Enterprise.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from core.cognition.decision_ledger import DecisionLedgerEngine
from core.cognition.evidence.envelope import EvidenceEnvelope
from core.cognition.evidence.store import EvidenceStore
from core.cognition.memory.context_fabric import ContextFabric
from core.cognition.orchestration.arbiter import (
    ArbitratedDecision,
    FederatedProposal,
    SovereignArbiter,
)

logger = logging.getLogger(__name__)


class FederatedCognitiveOrchestrator:
    def __init__(self, root_dir: Path = Path(r"G:\AI\E-zzio")):
        self.root_dir = root_dir
        self.arbiter = SovereignArbiter(root_dir=self.root_dir)
        self.context_fabric = ContextFabric(root_dir=self.root_dir)
        self.decision_engine = None
        self.evidence_store = None
        try:
            self.decision_engine = DecisionLedgerEngine(root_dir=self.root_dir)
            self.evidence_store = EvidenceStore(root_dir=self.root_dir, hmac_key=getattr(self.decision_engine, "hmac_key", None))
        except Exception:
            pass

    def run_collaborative_pipeline(
        self,
        task_id: str,
        task_description: str,
        local_analysis_output: str,
        gemini_reasoning_output: str,
        antigravity_execution_result: str,
    ) -> dict[str, Any]:
        """
        Executes a 3-stage collaborative pipeline:
        Stage 1: Local Analysis -> Evidence Envelope 1
        Stage 2: Cloud Reasoning -> Evidence Envelope 2
        Stage 3: Antigravity Execution -> Evidence Envelope 3
        Stage 4: Sovereign E-ZZIO Synthesis & Ledger Commit
        """
        key = getattr(self.decision_engine, "hmac_key", None)

        # 1. Evidence for Local Analysis
        env_local = EvidenceEnvelope.create(
            task_id=f"{task_id}-STAGE1",
            provider="local_ollama",
            model_name="qwen2.5:3b",
            capability="local_constraint_analysis",
            input_prompt=task_description,
            output_payload=local_analysis_output,
            execution_duration_ms=50.0,
            signing_key=key,
        )
        if self.evidence_store:
            self.evidence_store.store_evidence(env_local)

        # 2. Evidence for Cloud Reasoning
        env_cloud = EvidenceEnvelope.create(
            task_id=f"{task_id}-STAGE2",
            provider="cloud_gemini",
            model_name="gemini-3.1-pro-preview",
            capability="deep_reasoning_synthesis",
            input_prompt=f"{task_description}\nLocal context: {local_analysis_output}",
            output_payload=gemini_reasoning_output,
            execution_duration_ms=450.0,
            signing_key=key,
        )
        if self.evidence_store:
            self.evidence_store.store_evidence(env_cloud)

        # 3. Evidence for Agentic Execution
        env_agent = EvidenceEnvelope.create(
            task_id=f"{task_id}-STAGE3",
            provider="agent_antigravity",
            model_name="antigravity_agent",
            capability="agentic_refactor",
            input_prompt=gemini_reasoning_output,
            output_payload=antigravity_execution_result,
            execution_duration_ms=1200.0,
            signing_key=key,
        )
        if self.evidence_store:
            self.evidence_store.store_evidence(env_agent)

        # 4. Composite E-ZZIO Synthesis
        synthesis = {
            "pipeline_task_id": task_id,
            "status": "COLLABORATIVE_PIPELINE_SYNTHESIZED",
            "evidence_chain": [env_local.evidence_id, env_cloud.evidence_id, env_agent.evidence_id],
            "final_executable_payload": antigravity_execution_result,
        }

        # 5. Commit to Frozen Decision Ledger V10.0
        if self.decision_engine:
            try:
                self.decision_engine.record_decision(
                    subsystem="CognitiveOrchestrator",
                    decision_type="COLLABORATIVE_FEDERATED_PIPELINE",
                    context={"task_id": task_id, "evidence_chain": synthesis["evidence_chain"]},
                    action_payload=synthesis,
                    rationale=f"Successfully synthesized collaborative pipeline for {task_id} across Ollama, Gemini, Antigravity.",
                )
            except Exception as le:
                logger.warning(f"[ORCHESTRATOR] Ledger recording warning: {le}")

        return synthesis

    def run_consensus_arbitration(
        self,
        task_id: str,
        task_description: str,
        proposals: list[FederatedProposal],
    ) -> ArbitratedDecision:
        """Runs multi-proposal arbitration and records the winning consensus in the Ledger."""
        decision = self.arbiter.arbitrate(task_id, task_description, proposals)

        if self.decision_engine:
            if decision.status == "ARBITRATED_SUCCESS":
                try:
                    self.decision_engine.record_decision(
                        subsystem="CognitiveOrchestrator",
                        decision_type="MULTI_MODEL_CONSENSUS_ARBITRATION",
                        context={
                            "task_id": task_id,
                            "winning_provider": decision.winning_provider,
                            "winning_model": decision.winning_model,
                            "score": decision.consensus_score,
                        },
                        action_payload={"selected_action": decision.selected_action},
                        rationale=decision.arbitration_rationale,
                    )
                except Exception as le:
                    logger.warning(f"[ORCHESTRATOR] Ledger recording warning: {le}")
            elif decision.status == "SOVEREIGN_ABSTAIN":
                try:
                    self.decision_engine.record_decision(
                        subsystem="CognitiveOrchestrator",
                        decision_type="SOVEREIGN_COGNITIVE_ABSTENTION",
                        context={
                            "task_id": task_id,
                            "proposal_count": len(proposals),
                            "dissent_status": "SOVEREIGN_ABSTAIN",
                        },
                        action_payload={"selected_action": "ABORT_ABSTAIN", "participating_models": [p.model_name for p in proposals]},
                        rationale=decision.arbitration_rationale,
                    )
                except Exception as le:
                    logger.warning(f"[ORCHESTRATOR] Ledger recording warning: {le}")

        return decision

    def run_epistemic_arbitration(
        self,
        task_id: str,
        task_description: str,
        proposals: list[FederatedProposal],
    ):
        """Runs truth-weighted epistemic arbitration and commits verdict to Decision Ledger V10.0."""
        from core.cognition.epistemic.epistemic_arbiter import EpistemicArbiter
        epistemic_arb = EpistemicArbiter(root_dir=self.root_dir, evidence_store=self.evidence_store)
        verdict = epistemic_arb.arbitrate_epistemic(task_id, task_description, proposals)

        if self.decision_engine:
            try:
                self.decision_engine.record_decision(
                    subsystem="EpistemicEngine",
                    decision_type=verdict.epistemic_state,
                    context={
                        "task_id": task_id,
                        "verdict_id": verdict.verdict_id,
                        "epistemic_state": verdict.epistemic_state,
                        "winning_provider": verdict.winning_provider,
                        "winning_epistemic_weight": verdict.winning_epistemic_weight,
                    },
                    action_payload={"winning_action": verdict.winning_action},
                    rationale=verdict.rationale,
                )
            except Exception as le:
                logger.warning(f"[ORCHESTRATOR] Epistemic Ledger commit warning: {le}")

        return verdict
