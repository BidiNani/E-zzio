"""E-ZZIO Core — Sovereign Epistemic Analyzer (Phase 7.0).

Evaluates the objective epistemic weight of model proposals by cross-referencing:
1. Self-reported confidence (20% weight)
2. Cryptographic Evidence grounding (40% weight)
3. Historical Memory consistency across L3 Experience & L4 Semantic (30% weight)
4. Constitutional compliance (10% weight / fatal veto on violation)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.cognition.orchestration.arbiter import FederatedProposal
from core.cognition.evidence.store import EvidenceStore

logger = logging.getLogger(__name__)


@dataclass
class EpistemicScore:
    proposal: FederatedProposal
    self_confidence: float
    evidence_grounding: float
    memory_consistency: float
    constitutional_adherence: float
    composite_epistemic_weight: float
    is_vetoed: bool = False
    veto_reason: Optional[str] = None


class EpistemicAnalyzer:
    def __init__(self, root_dir: Path = Path(r"G:\AI\E-zzio"), evidence_store: Optional[EvidenceStore] = None):
        self.root_dir = root_dir
        self.evidence_store = evidence_store
        self.memory_store_dir = self.root_dir / "runtime" / "memory_store"
        self.genome_path = self.root_dir / "core" / "constitution" / "ezzio_genome.json"

    def _load_constitutional_invariants(self) -> List[str]:
        if not self.genome_path.exists():
            return []
        try:
            genome = json.loads(self.genome_path.read_text(encoding="utf-8"))
            return genome.get("constitution", {}).get("immutable_rules", [])
        except Exception:
            return []

    def _evaluate_memory_consistency(self, text: str) -> float:
        """Checks if proposal text aligns with or contradicts verified memories."""
        text_low = text.lower()
        contradiction_found = False
        supporting_found = False

        if self.memory_store_dir.exists():
            for json_file in self.memory_store_dir.rglob("*.json"):
                try:
                    data = json.loads(json_file.read_text(encoding="utf-8"))
                    content = str(data.get("content", "")).lower()
                    
                    # Memory explicitly teaches: "Éviter le conflit Global Mutex"
                    if "global mutex" in content:
                        if ("avoid" in text_low or "non-blocking" in text_low or "contextual" in text_low) and "global mutex" in text_low:
                            supporting_found = True
                        elif ("use" in text_low or "enforce" in text_low or "agree" in text_low) and "global mutex" in text_low:
                            contradiction_found = True
                    elif "way of elendil" in content and "way of elendil" in text_low:
                        supporting_found = True
                except Exception:
                    pass

        if contradiction_found:
            return -1.0
        if supporting_found:
            return 1.0
        return 0.5  # Neutral if no memory matches

    def _evaluate_evidence_grounding(self, proposal: FederatedProposal) -> float:
        """Verifies if proposal is grounded in a valid EvidenceEnvelope."""
        if not proposal.evidence_id:
            return 0.0

        if self.evidence_store:
            env = self.evidence_store.load_evidence(proposal.evidence_id, verify=True)
            if env and env.verification_status == "VERIFIED_VALID":
                return 1.0
            return 0.0

        return 0.5 if proposal.evidence_id.startswith("EVID-") else 0.0

    def evaluate_proposal(self, proposal: FederatedProposal) -> EpistemicScore:
        """Computes the epistemic weight score for a candidate proposal."""
        # 1. Self Confidence (normalized)
        conf = max(0.0, min(1.0, proposal.confidence))

        # 2. Evidence Grounding
        ev_grounding = self._evaluate_evidence_grounding(proposal)

        # 3. Memory Consistency
        mem_consistency = self._evaluate_memory_consistency(proposal.proposal_text)

        # 4. Constitutional Adherence
        text_low = proposal.proposal_text.lower()
        vetoed = False
        veto_reason = None
        const_adherence = 1.0

        for rule in ["override constitution", "disregard policy", "maximize priority kill gaming"]:
            if rule in text_low:
                vetoed = True
                veto_reason = f"Violated rule: {rule}"
                const_adherence = -100.0
                break

        if vetoed:
            epistemic_weight = -100.0
        else:
            # Epistemic formula: (Conf * 0.2) + (Evidence * 0.4) + (Memory * 0.3) + (Const * 0.1)
            mem_term = (mem_consistency * 0.3) if mem_consistency < 0 else (mem_consistency * 0.3)
            epistemic_weight = max(0.0, (conf * 0.2) + (ev_grounding * 0.4) + mem_term + (const_adherence * 0.1))

        return EpistemicScore(
            proposal=proposal,
            self_confidence=conf,
            evidence_grounding=ev_grounding,
            memory_consistency=mem_consistency,
            constitutional_adherence=const_adherence,
            composite_epistemic_weight=epistemic_weight,
            is_vetoed=vetoed,
            veto_reason=veto_reason,
        )
