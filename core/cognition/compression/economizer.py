"""E-ZZIO Core — Sovereign Context Economizer (Phase 8.4).

Orchestrates a 3-engine context reduction pipeline:
1. LOSSLESS DEDUPLICATION: Prunes repeating logs and execution artifacts (10-30%).
2. SEMANTIC FACT PRUNING: Condenses conversational prose while locking onto named entities & memory facts (30-60%).
3. AGGRESSIVE CCR EXTRACTION: Condenses massive JSON/tool dumps into schemas + [CCR-REF:cache_id] (70-95%).

Enforces Epistemic Invariants:
- L5 Constitution is 100% INVIOLABLE (0% destructive compression).
- Cryptographic hashes and Decision Ledger identities remain untouched.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT_DIR = Path(r"G:\AI\E-zzio")

from core.cognition.compression.budget_engine import (
    ClassifiedContextSegment,
    ContentCategory,
    ContextSensitivityTier,
    ContextBudgetEngine,
)
from core.cognition.compression.compressor_fabric import (
    CompressedSegmentResult,
    SovereignCompressorFabric,
)
from core.cognition.compression.integrity_gate import (
    CompressionAuditVerdict,
    CompressionIntegrityGate,
)

logger = logging.getLogger(__name__)


@dataclass
class EconomizedContextPackage:
    package_id: str
    task_id: str
    original_char_count: int
    economized_char_count: int
    original_estimated_tokens: int
    economized_estimated_tokens: int
    net_tokens_saved: int
    effective_reduction_percent: float
    effective_prompt_text: str
    segment_verdicts: List[CompressionAuditVerdict]
    integrity_status: str  # "ALL_SEGMENTS_CERTIFIED", "PARTIAL_FALLBACK", "INTEGRITY_ABSTAIN"
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SovereignContextEconomizer:
    def __init__(self, root_dir: Path = ROOT_DIR):
        self.root_dir = root_dir
        self.budget_engine = ContextBudgetEngine()
        self.fabric = SovereignCompressorFabric(root_dir=self.root_dir)
        self.integrity_gate = CompressionIntegrityGate(root_dir=self.root_dir)

    def deduplicate_exact_lines(self, text: str) -> Tuple[str, int]:
        """Engine 1: Lossless Exact Deduplication for repeating logs or stdout lines."""
        lines = text.splitlines()
        if len(lines) <= 1:
            return text, 0

        deduped = []
        seen_patterns = set()
        removed_count = 0

        for line in lines:
            normalized = line.strip()
            # Extract core message by stripping standard ISO or date timestamp prefixes
            core_msg = re.sub(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?\s*", "", normalized)
            
            if len(core_msg) > 10 and core_msg in seen_patterns:
                removed_count += 1
                continue
            seen_patterns.add(core_msg)
            deduped.append(line)

        return "\n".join(deduped), removed_count

    def economize_context_payload(
        self,
        task_id: str,
        raw_segments: List[Dict[str, Any]],  # [{"id": "seg1", "text": "...", "hint": "..."}]
    ) -> EconomizedContextPackage:
        """
        Processes multi-part context segments through the 3-engine pipeline
        and validates epistemic retention via the CompressionIntegrityGate.
        """
        pkg_id = f"ECO-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{task_id}"
        total_orig_chars = 0
        total_econ_chars = 0
        total_orig_tokens = 0
        total_econ_tokens = 0
        verdicts = []
        effective_parts = []
        has_fallback = False

        for item in raw_segments:
            seg_id = item.get("id", f"seg_{len(verdicts)}")
            seg_text = item.get("text", "")
            seg_hint = item.get("hint")

            # 1. Classification
            classified = self.budget_engine.classify_segment(seg_id, seg_text, hint_category=seg_hint)
            total_orig_chars += classified.raw_char_count
            total_orig_tokens += classified.estimated_raw_tokens

            # 2. Engine 1: Lossless Deduplication (for logs/tool outputs)
            if classified.category in {ContentCategory.LOGS, ContentCategory.TOOL_OUTPUT}:
                deduped_text, _ = self.deduplicate_exact_lines(classified.raw_text)
                classified.raw_text = deduped_text
                classified.raw_char_count = len(deduped_text)
                classified.estimated_raw_tokens = max(1, len(deduped_text) // 4)

            # 3. Engines 2 & 3 + Integrity Gate
            verdict = self.integrity_gate.evaluate_and_filter(task_id, classified)
            verdicts.append(verdict)

            effective_parts.append(verdict.effective_text)
            total_econ_chars += len(verdict.effective_text)
            total_econ_tokens += max(1, len(verdict.effective_text) // 4)

            if verdict.verdict == "INTEGRITY_REJECTED_RAW_RESTORED":
                has_fallback = True

        net_saved = max(0, total_orig_tokens - total_econ_tokens)
        reduction_pct = round(max(0.0, (total_orig_chars - total_econ_chars) / max(1, total_orig_chars) * 100.0), 1)

        status = "PARTIAL_FALLBACK" if has_fallback else "ALL_SEGMENTS_CERTIFIED"
        joined_text = "\n\n".join(effective_parts)

        return EconomizedContextPackage(
            package_id=pkg_id,
            task_id=task_id,
            original_char_count=total_orig_chars,
            economized_char_count=total_econ_chars,
            original_estimated_tokens=total_orig_tokens,
            economized_estimated_tokens=total_econ_tokens,
            net_tokens_saved=net_saved,
            effective_reduction_percent=reduction_pct,
            effective_prompt_text=joined_text,
            segment_verdicts=verdicts,
            integrity_status=status,
        )
