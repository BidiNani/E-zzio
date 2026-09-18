"""E-ZZIO Core — Sovereign Epistemic Arbiter (Phase 7.0).

Performs evidence-grounded cognitive arbitration, distinguishing between:
- EPISTEMIC_CERTIFIED_CONSENSUS: True agreement backed by evidence & memory.
- EPISTEMIC_MINORITY_TRUTH: Minority proposal with verified grounding beating ungrounded majority.
- EPISTEMIC_COLLUSIVE_HALLUCINATION_REJECTED: Majority consensus rejected due to evidence/memory conflict.
- EPISTEMIC_SOVEREIGN_ABSTAIN: Insufficient proof to reach certainty.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from core.cognition.epistemic.epistemic_analyzer import EpistemicAnalyzer, EpistemicScore
from core.cognition.evidence.store import EvidenceStore
from core.cognition.orchestration.arbiter import FederatedProposal

logger = logging.getLogger(__name__)


@dataclass
class EpistemicVerdict:
    verdict_id: str
    task_id: str
    timestamp_utc: str
    epistemic_state: str  # "EPISTEMIC_CERTIFIED_CONSENSUS", "EPISTEMIC_MINORITY_TRUTH", "EPISTEMIC_SOVEREIGN_ABSTAIN"
    winning_provider: str
    winning_model: str
    winning_action: str
    winning_epistemic_weight: float
    rationale: str
    participating_scores: list[EpistemicScore]


class EpistemicArbiter:
    def __init__(self, root_dir: Path = Path(r"G:\AI\E-zzio"), evidence_store: EvidenceStore | None = None):
        self.root_dir = root_dir
        self.evidence_store = evidence_store
        self.analyzer = EpistemicAnalyzer(root_dir=self.root_dir, evidence_store=self.evidence_store)

    def arbitrate_epistemic(
        self,
        task_id: str,
        task_description: str,
        proposals: list[FederatedProposal],
    ) -> EpistemicVerdict:
        """Arbitrates candidate proposals using epistemic grounding and truth verification."""
        if not proposals:
            raise ValueError("FAIL-CLOSED: Epistemic arbiter requires at least one proposal.")

        ts = datetime.now(UTC).isoformat()
        verdict_id = f"EPI-{datetime.now(UTC).strftime('%Y%m%d')}-{task_id}"

        scored = [self.analyzer.evaluate_proposal(p) for p in proposals]
        scored.sort(key=lambda x: x.composite_epistemic_weight, reverse=True)

        top = scored[0]

        # 1. Fatal Constitutional Veto Check
        if top.is_vetoed or top.composite_epistemic_weight < 0:
            return EpistemicVerdict(
                verdict_id=verdict_id,
                task_id=task_id,
                timestamp_utc=ts,
                epistemic_state="EPISTEMIC_SOVEREIGN_ABSTAIN",
                winning_provider="NONE",
                winning_model="NONE",
                winning_action="ABORT_VETO",
                winning_epistemic_weight=0.0,
                rationale=f"Fatal constitutional veto: {top.veto_reason}",
                participating_scores=scored,
            )

        # 2. Check for Collusive Hallucinations (Majority claiming something contradicted by memory)
        memory_contradicting = [s for s in scored if s.memory_consistency == -1.0]
        if len(memory_contradicting) >= 2 and top.memory_consistency == -1.0:
            return EpistemicVerdict(
                verdict_id=verdict_id,
                task_id=task_id,
                timestamp_utc=ts,
                epistemic_state="EPISTEMIC_SOVEREIGN_ABSTAIN",
                winning_provider="NONE",
                winning_model="NONE",
                winning_action="ABORT_COLLUSIVE_HALLUCINATION",
                winning_epistemic_weight=0.0,
                rationale="Majority proposals directly contradicted verified historical L3/L4 Memory. Consensus rejected.",
                participating_scores=scored,
            )

        # 3. Check for Minority Truth Victory (e.g. 1 proposal with strong grounding beats multiple ungrounded/contradictory proposals)
        if len(scored) >= 2 and top.composite_epistemic_weight >= 0.70:
            lower_scores = scored[1:]
            if all(ls.composite_epistemic_weight < 0.60 or ls.memory_consistency < 0 for ls in lower_scores):
                return EpistemicVerdict(
                    verdict_id=verdict_id,
                    task_id=task_id,
                    timestamp_utc=ts,
                    epistemic_state="EPISTEMIC_MINORITY_TRUTH",
                    winning_provider=top.proposal.provider,
                    winning_model=top.proposal.model_name,
                    winning_action=top.proposal.suggested_action or top.proposal.proposal_text,
                    winning_epistemic_weight=top.composite_epistemic_weight,
                    rationale=f"Minority truth victory: {top.proposal.provider}:{top.proposal.model_name} had verified evidence/memory backing overruling ungrounded candidates.",
                    participating_scores=scored,
                )

        # 4. Check for Epistemic Certified Consensus
        if top.composite_epistemic_weight >= 0.70:
            return EpistemicVerdict(
                verdict_id=verdict_id,
                task_id=task_id,
                timestamp_utc=ts,
                epistemic_state="EPISTEMIC_CERTIFIED_CONSENSUS",
                winning_provider=top.proposal.provider,
                winning_model=top.proposal.model_name,
                winning_action=top.proposal.suggested_action or top.proposal.proposal_text,
                winning_epistemic_weight=top.composite_epistemic_weight,
                rationale=f"Epistemic certified consensus achieved with weight {top.composite_epistemic_weight:.2f}.",
                participating_scores=scored,
            )

        # 5. Default: Sovereign Abstain when truth cannot be certified
        return EpistemicVerdict(
            verdict_id=verdict_id,
            task_id=task_id,
            timestamp_utc=ts,
            epistemic_state="EPISTEMIC_SOVEREIGN_ABSTAIN",
            winning_provider="NONE",
            winning_model="NONE",
            winning_action="ABORT_INSUFFICIENT_PROOF",
            winning_epistemic_weight=top.composite_epistemic_weight,
            rationale=f"Insufficient epistemic proof (Top weight {top.composite_epistemic_weight:.2f} < 0.70 threshold). Abstaining safely.",
            participating_scores=scored,
        )
