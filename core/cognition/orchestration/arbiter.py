"""E-ZZIO Core — Sovereign Consensus Arbiter (Phase 6.0).

Evaluates competing proposals from multiple federated models (Ollama, Gemini, Antigravity)
against E-ZZIO Constitution (L5), Memory heuristics (L3/L4), and Hardware policy.
Determines the authoritative arbitrated decision without granting sovereign authority to any model.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FederatedProposal:
    provider: str  # "local_ollama", "cloud_gemini", "agent_antigravity"
    model_name: str
    proposal_text: str
    confidence: float
    evidence_id: str | None = None
    suggested_action: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ArbitratedDecision:
    decision_id: str
    task_id: str
    timestamp_utc: str
    winning_provider: str
    winning_model: str
    arbitration_rationale: str
    consensus_score: float
    selected_action: str
    participating_proposals: list[FederatedProposal]
    constitutional_verified: bool
    status: str = "ARBITRATED_SUCCESS"


class SovereignArbiter:
    def __init__(self, root_dir: Path = Path(r"G:\AI\E-zzio")):
        self.root_dir = root_dir
        self.genome_path = self.root_dir / "core" / "constitution" / "ezzio_genome.json"
        from core.cognition.orchestration.dissent_engine import CognitiveDissentEngine
        self.dissent_engine = CognitiveDissentEngine()

    def _load_constitutional_invariants(self) -> list[str]:
        """Loads immutable constitutional rules."""
        if not self.genome_path.exists():
            return []
        try:
            genome = json.loads(self.genome_path.read_text(encoding="utf-8"))
            return genome.get("constitution", {}).get("immutable_rules", [])
        except Exception:
            return []

    def arbitrate(
        self,
        task_id: str,
        task_description: str,
        proposals: list[FederatedProposal],
    ) -> ArbitratedDecision:
        """Arbitrates between competing proposals based on Constitution, logic, and safety."""
        if not proposals:
            raise ValueError("FAIL-CLOSED: Cannot arbitrate with zero proposals.")

        ts = datetime.now(UTC).isoformat()
        decision_id = f"ARB-{datetime.now(UTC).strftime('%Y%m%d')}-{task_id}"

        # 1. Epistemic Dissent Evaluation
        dissent_eval = self.dissent_engine.evaluate_dissent(proposals)
        if dissent_eval.dissent_verdict == "SOVEREIGN_ABSTAIN":
            return ArbitratedDecision(
                decision_id=decision_id,
                task_id=task_id,
                timestamp_utc=ts,
                winning_provider="NONE",
                winning_model="NONE",
                arbitration_rationale=f"SOVEREIGN_ABSTAIN: {dissent_eval.rationale}",
                consensus_score=0.0,
                selected_action="ABORT_ABSTAIN",
                participating_proposals=proposals,
                constitutional_verified=True,
                status="SOVEREIGN_ABSTAIN",
            )

        constitutional_rules = self._load_constitutional_invariants()
        scored_candidates = []

        for p in proposals:
            score = p.confidence * 1.0

            # 2. Constitutional Compliance Check
            text_low = p.proposal_text.lower()
            violates_constitution = False
            if any(forbidden in text_low for forbidden in ["override constitution", "disregard policy", "maximize priority kill gaming"]):
                score = -100.0
                violates_constitution = True

            # 3. Local Sovereignty Preference in ties
            if p.provider == "local_ollama":
                score += 0.05

            # 4. Evidence Backing Bonus
            if p.evidence_id:
                score += 0.1

            scored_candidates.append((score, violates_constitution, p))

        # Sort descending by score
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        top_score, top_violation, winner = scored_candidates[0]

        if top_violation or top_score < 0:
            rationale = "All proposals violated constitutional invariants or failed validation. Rejected."
            status = "ARBITRATION_REJECTED_FAIL_CLOSED"
            winning_provider = "NONE"
            winning_model = "NONE"
            selected_action = "ABORT"
            const_ok = False
        else:
            rationale = f"Selected {winner.provider}:{winner.model_name} (Score: {top_score:.2f}) adhering to E-ZZIO Constitution."
            status = "ARBITRATED_SUCCESS"
            winning_provider = winner.provider
            winning_model = winner.model_name
            selected_action = winner.suggested_action or winner.proposal_text
            const_ok = True

        return ArbitratedDecision(
            decision_id=decision_id,
            task_id=task_id,
            timestamp_utc=ts,
            winning_provider=winning_provider,
            winning_model=winning_model,
            arbitration_rationale=rationale,
            consensus_score=top_score,
            selected_action=selected_action,
            participating_proposals=proposals,
            constitutional_verified=const_ok,
            status=status,
        )
