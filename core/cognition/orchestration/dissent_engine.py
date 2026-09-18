"""E-ZZIO Core — Cognitive Dissent & Uncertainty Engine (Phase 6.1).

Evaluates model dispersion, epistemic uncertainty, and dissent entropy across federated proposals.
Determines whether to ACCEPT_WINNER, RETRY_WITH_CONTEXT, or SOVEREIGN_ABSTAIN.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from core.cognition.orchestration.arbiter import FederatedProposal


@dataclass
class DissentEvaluation:
    entropy: float
    max_confidence: float
    min_confidence: float
    confidence_spread: float
    dissent_verdict: str  # "PROCEED_ARBITRATION", "RETRY_SUGGESTED", "SOVEREIGN_ABSTAIN", "HUMAN_ESCALATION"
    rationale: str


class CognitiveDissentEngine:
    MIN_CONFIDENCE_THRESHOLD = 0.65
    MAX_PERMISSIBLE_DISSENT_ENTROPY = 0.80

    def evaluate_dissent(self, proposals: list[FederatedProposal]) -> DissentEvaluation:
        """Analyzes divergence across multiple proposals and calculates dissent entropy."""
        if not proposals:
            return DissentEvaluation(
                entropy=1.0,
                max_confidence=0.0,
                min_confidence=0.0,
                confidence_spread=0.0,
                dissent_verdict="SOVEREIGN_ABSTAIN",
                rationale="Zero proposals provided; abstaining safely.",
            )

        confidences = [max(0.01, min(0.99, p.confidence)) for p in proposals]
        max_conf = max(confidences)
        min_conf = min(confidences)
        spread = max_conf - min_conf

        # Calculate normalized Shannon entropy of normalized confidences
        total_conf = sum(confidences)
        probs = [c / total_conf for c in confidences]
        raw_entropy = -sum(p * math.log2(p) for p in probs)
        max_possible_entropy = math.log2(len(proposals)) if len(proposals) > 1 else 1.0
        normalized_entropy = raw_entropy / max_possible_entropy if max_possible_entropy > 0 else 0.0

        # Check 1: Insufficient overall confidence across all models
        if max_conf < self.MIN_CONFIDENCE_THRESHOLD:
            return DissentEvaluation(
                entropy=normalized_entropy,
                max_confidence=max_conf,
                min_confidence=min_conf,
                confidence_spread=spread,
                dissent_verdict="SOVEREIGN_ABSTAIN",
                rationale=f"Insufficient maximum confidence ({max_conf:.2f} < {self.MIN_CONFIDENCE_THRESHOLD}); cannot manufacture certainty.",
            )

        # Check 2: High Entropy with low spread (Multi-Model Irreconcilable Divergence)
        # e.g. 3 models with confidence 0.88, 0.87, 0.86 with totally different suggestions
        distinct_actions = len({p.proposal_text.strip().lower() for p in proposals})
        if len(proposals) >= 3 and distinct_actions >= 3 and normalized_entropy > self.MAX_PERMISSIBLE_DISSENT_ENTROPY and spread < 0.05:
            return DissentEvaluation(
                entropy=normalized_entropy,
                max_confidence=max_conf,
                min_confidence=min_conf,
                confidence_spread=spread,
                dissent_verdict="SOVEREIGN_ABSTAIN",
                rationale=f"Deep epistemic dissent detected across {len(proposals)} models (Entropy: {normalized_entropy:.2f}, Spread: {spread:.2f}); abstaining from arbitrary tie-breaking.",
            )

        # Check 3: Clear dominant winner
        return DissentEvaluation(
            entropy=normalized_entropy,
            max_confidence=max_conf,
            min_confidence=min_conf,
            confidence_spread=spread,
            dissent_verdict="PROCEED_ARBITRATION",
            rationale=f"Confidence and entropy within acceptable boundaries (Max Conf: {max_conf:.2f}, Entropy: {normalized_entropy:.2f}).",
        )
