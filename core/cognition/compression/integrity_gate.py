"""E-ZZIO Core — Sovereign Compression Integrity Gate (Phase 8.2).

Evaluates compressed context segments before delivery to downstream models:
- Validates that zero L5 Constitutional rules were altered or compressed.
- Validates that key named entities and numeric constraints are preserved.
- Automatically reverts to uncompressed original if integrity score drops below threshold.
- Commits compression audits to the Frozen Decision Ledger V10.0 Enterprise.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from core.cognition.compression.budget_engine import (
    ClassifiedContextSegment,
    ContextSensitivityTier,
)
from core.cognition.compression.compressor_fabric import (
    SovereignCompressorFabric,
)
from core.cognition.decision_ledger import DecisionLedgerEngine

logger = logging.getLogger(__name__)


@dataclass
class CompressionAuditVerdict:
    segment_id: str
    verdict: str  # "COMPRESSION_CERTIFIED", "INTEGRITY_REJECTED_RAW_RESTORED"
    tokens_saved: int
    compression_ratio: float
    effective_text: str
    rationale: str
    timestamp_utc: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class CompressionIntegrityGate:
    def __init__(self, root_dir: Path = Path(r"G:\AI\E-zzio")):
        self.root_dir = root_dir
        self.fabric = SovereignCompressorFabric(root_dir=self.root_dir)
        self.decision_engine = None
        try:
            self.decision_engine = DecisionLedgerEngine(root_dir=self.root_dir)
        except Exception:
            pass

    def evaluate_and_filter(
        self,
        task_id: str,
        segment: ClassifiedContextSegment,
    ) -> CompressionAuditVerdict:
        """
        Compresses segment and enforces strict epistemic verification.
        Reverts to raw uncompressed text if fact retention is breached.
        """
        comp_res = self.fabric.compress_segment(segment)

        # Invariant 1: Inviolable Tier MUST be 0% loss
        if segment.tier == ContextSensitivityTier.INVIOLABLE:
            if comp_res.compressed_text != segment.raw_text:
                return self._build_verdict(
                    task_id=task_id,
                    segment_id=segment.segment_id,
                    verdict="INTEGRITY_REJECTED_RAW_RESTORED",
                    tokens_saved=0,
                    ratio=0.0,
                    text=segment.raw_text,
                    rationale="SECURITY VETO: Inviolable Tier context cannot be modified or compressed.",
                )
            return self._build_verdict(
                task_id=task_id,
                segment_id=segment.segment_id,
                verdict="COMPRESSION_CERTIFIED",
                tokens_saved=0,
                ratio=0.0,
                text=segment.raw_text,
                rationale="Inviolable context passed untouched (100% preservation).",
            )

        # Invariant 2: Semantic Integrity & Fact Preservation Check
        # A. Critical named entities / system concepts
        for keyword in ["global mutex", "way of elendil", "decision_ledger", "hmac"]:
            if keyword in segment.raw_text.lower() and keyword not in comp_res.compressed_text.lower():
                logger.warning(f"[COMPRESSION GATE] Fact loss detected for '{keyword}'. Reverting to raw original.")
                raw_orig = self.fabric.retrieve_from_ccr_cache(comp_res.cache_id) or segment.raw_text
                return self._build_verdict(
                    task_id=task_id,
                    segment_id=segment.segment_id,
                    verdict="INTEGRITY_REJECTED_RAW_RESTORED",
                    tokens_saved=0,
                    ratio=0.0,
                    text=raw_orig,
                    rationale=f"INTEGRITY FAIL: Critical fact '{keyword}' lost in compression; restored uncompressed original via CCR.",
                )

        # B. Negation & Numerical/IP Identity Preservation
        import re
        negations = ["not", "never", "no", "non", "jamais", "aucun", "interdit", "prohibited"]
        for neg in negations:
            # If a standalone negation exists in raw text, it must exist in compressed text
            if re.search(rf"\b{neg}\b", segment.raw_text, re.IGNORECASE) and not re.search(rf"\b{neg}\b", comp_res.compressed_text, re.IGNORECASE):
                logger.warning(f"[COMPRESSION GATE] Negation loss detected for '{neg}'. Reverting to raw original.")
                raw_orig = self.fabric.retrieve_from_ccr_cache(comp_res.cache_id) or segment.raw_text
                return self._build_verdict(
                    task_id=task_id,
                    segment_id=segment.segment_id,
                    verdict="INTEGRITY_REJECTED_RAW_RESTORED",
                    tokens_saved=0,
                    ratio=0.0,
                    text=raw_orig,
                    rationale=f"INTEGRITY FAIL: Negation '{neg}' stripped during compression; restored uncompressed original via CCR.",
                )

        # Extract IPs / Ports / Numbers > 10
        numbers_raw = set(re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}\b|\b\d{2,5}\b", segment.raw_text))
        for num in numbers_raw:
            if num not in comp_res.compressed_text:
                logger.warning(f"[COMPRESSION GATE] Numerical entity '{num}' lost in compression. Reverting to raw original.")
                raw_orig = self.fabric.retrieve_from_ccr_cache(comp_res.cache_id) or segment.raw_text
                return self._build_verdict(
                    task_id=task_id,
                    segment_id=segment.segment_id,
                    verdict="INTEGRITY_REJECTED_RAW_RESTORED",
                    tokens_saved=0,
                    ratio=0.0,
                    text=raw_orig,
                    rationale=f"INTEGRITY FAIL: Numerical entity '{num}' mutated/lost during compression; restored uncompressed original via CCR.",
                )

        # Successful certified compression
        tokens_saved = max(0, comp_res.original_estimated_tokens - comp_res.compressed_estimated_tokens)
        return self._build_verdict(
            task_id=task_id,
            segment_id=segment.segment_id,
            verdict="COMPRESSION_CERTIFIED",
            tokens_saved=tokens_saved,
            ratio=comp_res.compression_ratio_percent,
            text=comp_res.compressed_text,
            rationale=f"Compression certified with {comp_res.compression_ratio_percent:.1f}% reduction via {comp_res.compression_strategy}.",
        )

    def _build_verdict(
        self,
        task_id: str,
        segment_id: str,
        verdict: str,
        tokens_saved: int,
        ratio: float,
        text: str,
        rationale: str,
    ) -> CompressionAuditVerdict:
        v = CompressionAuditVerdict(
            segment_id=segment_id,
            verdict=verdict,
            tokens_saved=tokens_saved,
            compression_ratio=ratio,
            effective_text=text,
            rationale=rationale,
        )

        if self.decision_engine:
            try:
                self.decision_engine.record_decision(
                    subsystem="ContextCompressor",
                    decision_type=verdict,
                    context={"task_id": task_id, "segment_id": segment_id, "tokens_saved": tokens_saved, "ratio": ratio},
                    action_payload={"effective_char_length": len(text)},
                    rationale=rationale,
                )
            except Exception as le:
                logger.warning(f"[COMPRESSION GATE] Ledger recording warning: {le}")

        return v
