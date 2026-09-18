"""E-ZZIO Core — Sovereign Context Budget & Classification Engine (Phase 8.2).

Classifies context segments into 3 sensitivity tiers:
1. TIER 1 (INVIOLABLE): L5 Constitution, Invariants, Secrets, Proof Hashes -> 0% Compression allowed.
2. TIER 2 (SEMANTIC): L3 Experience, L4 Semantic facts -> Light Fact-Preserving Compression.
3. TIER 3 (BULK_REDUNDANT): Tool outputs, command logs, JSON dumps -> Aggressive Content-Aware Compression.
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ContextSensitivityTier(str, enum.Enum):
    INVIOLABLE = "INVIOLABLE"      # 0% Loss (Exact preserve)
    SEMANTIC = "SEMANTIC"          # Fact-preserving light compression
    BULK_REDUNDANT = "BULK_REDUNDANT"  # Aggressive compression with CCR cache


class ContentCategory(str, enum.Enum):
    CONSTITUTION = "CONSTITUTION"
    PROSE = "PROSE"
    CODE = "CODE"
    JSON_DATA = "JSON_DATA"
    LOGS = "LOGS"
    TOOL_OUTPUT = "TOOL_OUTPUT"


@dataclass
class ClassifiedContextSegment:
    segment_id: str
    category: ContentCategory
    tier: ContextSensitivityTier
    raw_text: str
    raw_char_count: int
    estimated_raw_tokens: int


class ContextBudgetEngine:
    def __init__(self):
        pass

    def classify_segment(self, segment_id: str, text: str, hint_category: str | None = None) -> ClassifiedContextSegment:
        """Classifies a context segment into its appropriate tier and strategy."""
        clean_text = text.strip()
        chars = len(clean_text)
        est_tokens = max(1, chars // 4)

        text_low = clean_text.lower()

        # 1. Tier 1: Inviolable Constitution / System Directives
        if (
            "sovereign rule" in text_low
            or "immutable_rules" in text_low
            or "constitution" in text_low
            or "decision_ledger" in text_low
            or "ezzio sovereign context" in text_low
            or hint_category == "CONSTITUTION"
        ):
            return ClassifiedContextSegment(
                segment_id=segment_id,
                category=ContentCategory.CONSTITUTION,
                tier=ContextSensitivityTier.INVIOLABLE,
                raw_text=clean_text,
                raw_char_count=chars,
                estimated_raw_tokens=est_tokens,
            )

        # 2. Tier 3: Structured JSON Data
        if (clean_text.startswith("{") and clean_text.endswith("}")) or (clean_text.startswith("[") and clean_text.endswith("]")) or hint_category == "JSON_DATA":
            return ClassifiedContextSegment(
                segment_id=segment_id,
                category=ContentCategory.JSON_DATA,
                tier=ContextSensitivityTier.BULK_REDUNDANT,
                raw_text=clean_text,
                raw_char_count=chars,
                estimated_raw_tokens=est_tokens,
            )

        # 3. Tier 3: Logs & Tool Outputs
        if "traceback" in text_low or "stderr:" in text_low or "stdout:" in text_low or hint_category in {"LOGS", "TOOL_OUTPUT"}:
            return ClassifiedContextSegment(
                segment_id=segment_id,
                category=ContentCategory.TOOL_OUTPUT,
                tier=ContextSensitivityTier.BULK_REDUNDANT,
                raw_text=clean_text,
                raw_char_count=chars,
                estimated_raw_tokens=est_tokens,
            )

        # 4. Tier 3: Code blocks
        if "def " in clean_text or "class " in clean_text or "import " in clean_text or hint_category == "CODE":
            return ClassifiedContextSegment(
                segment_id=segment_id,
                category=ContentCategory.CODE,
                tier=ContextSensitivityTier.BULK_REDUNDANT,
                raw_text=clean_text,
                raw_char_count=chars,
                estimated_raw_tokens=est_tokens,
            )

        # 5. Tier 2: Semantic Memory / Natural Language Prose
        return ClassifiedContextSegment(
            segment_id=segment_id,
            category=ContentCategory.PROSE,
            tier=ContextSensitivityTier.SEMANTIC,
            raw_text=clean_text,
            raw_char_count=chars,
            estimated_raw_tokens=est_tokens,
        )
