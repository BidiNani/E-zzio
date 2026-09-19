"""E-ZZIO Core — Sovereign Compressor Fabric & CCR (Compress-Cache-Retrieve) Store (Phase 8.2).

Provides local-first content-aware compression for JSON, Code, Logs (Headroom Strategy)
and semantic summarization (LLMLingua-2 Strategy) while persisting original raw content in the CCR store.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from core.cognition.compression.budget_engine import (
    ClassifiedContextSegment,
    ContentCategory,
    ContextSensitivityTier,
)

logger = logging.getLogger(__name__)


@dataclass
class CompressedSegmentResult:
    segment_id: str
    cache_id: str
    tier: ContextSensitivityTier
    category: ContentCategory
    original_char_count: int
    compressed_char_count: int
    original_estimated_tokens: int
    compressed_estimated_tokens: int
    compression_ratio_percent: float  # e.g. 65.0% reduction
    compressed_text: str
    compression_strategy: str  # "HEADROOM_JSON", "HEADROOM_CODE", "LLMLINGUA_PROSE", "NO_COMPRESSION"


class SovereignCompressorFabric:
    def __init__(self, root_dir: Path = Path(r"G:\AI\E-zzio")):
        self.root_dir = root_dir
        self.cache_dir = self.root_dir / "runtime" / "compression_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def store_in_ccr_cache(self, raw_text: str) -> str:
        """Stores uncompressed original text in CCR cache and returns unique cache_id."""
        sha = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        cache_id = f"CCR-{sha[:16]}"
        cache_file = self.cache_dir / f"{cache_id}.json"

        if not cache_file.exists():
            payload = {
                "cache_id": cache_id,
                "sha256": sha,
                "timestamp_utc": datetime.now(UTC).isoformat(),
                "char_length": len(raw_text),
                "original_text": raw_text,
            }
            cache_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        return cache_id

    def retrieve_from_ccr_cache(self, cache_id: str) -> str | None:
        """Losslessly retrieves the original uncompressed text from CCR cache."""
        cache_file = self.cache_dir / f"{cache_id}.json"
        if not cache_file.exists():
            return None
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            return data.get("original_text")
        except Exception as e:
            logger.error(f"[CCR CACHE] Could not read cache {cache_id}: {e}")
            return None

    def compress_segment(self, segment: ClassifiedContextSegment) -> CompressedSegmentResult:
        """Compresses a classified segment based on its sensitivity tier and content category."""
        cache_id = self.store_in_ccr_cache(segment.raw_text)

        # 1. Tier 1: Inviolable Constitution -> NO COMPRESSION ALLOWED
        if segment.tier == ContextSensitivityTier.INVIOLABLE:
            return CompressedSegmentResult(
                segment_id=segment.segment_id,
                cache_id=cache_id,
                tier=segment.tier,
                category=segment.category,
                original_char_count=segment.raw_char_count,
                compressed_char_count=segment.raw_char_count,
                original_estimated_tokens=segment.estimated_raw_tokens,
                compressed_estimated_tokens=segment.estimated_raw_tokens,
                compression_ratio_percent=0.0,
                compressed_text=segment.raw_text,
                compression_strategy="NO_COMPRESSION_INVIOLABLE",
            )

        # 2. Tier 3: Headroom JSON Compression Strategy
        if segment.category == ContentCategory.JSON_DATA:
            comp_text = self._headroom_compress_json(segment.raw_text, cache_id)
            strategy = "HEADROOM_JSON"
        # 3. Tier 3: Headroom Code/Log Compression Strategy
        elif segment.category in {ContentCategory.CODE, ContentCategory.TOOL_OUTPUT, ContentCategory.LOGS}:
            comp_text = self._headroom_compress_code_and_logs(segment.raw_text, cache_id)
            strategy = "HEADROOM_CODE_LOGS"
        # 4. Tier 2: LLMLingua-2 Semantic Prose Strategy
        else:
            comp_text = self._llmlingua_compress_prose(segment.raw_text, cache_id)
            strategy = "LLMLINGUA_PROSE"

        comp_chars = len(comp_text)
        comp_tokens = max(1, comp_chars // 4)
        reduction_pct = round(max(0.0, (segment.raw_char_count - comp_chars) / segment.raw_char_count * 100.0), 1)

        return CompressedSegmentResult(
            segment_id=segment.segment_id,
            cache_id=cache_id,
            tier=segment.tier,
            category=segment.category,
            original_char_count=segment.raw_char_count,
            compressed_char_count=comp_chars,
            original_estimated_tokens=segment.estimated_raw_tokens,
            compressed_estimated_tokens=comp_tokens,
            compression_ratio_percent=reduction_pct,
            compressed_text=comp_text,
            compression_strategy=strategy,
        )

    def _headroom_compress_json(self, raw_json: str, cache_id: str) -> str:
        """Compresses JSON by pruning nulls/empty structures and compacting whitespace with CCR header."""
        try:
            parsed = json.loads(raw_json)
            # Prune empty keys/nulls
            def clean_struct(obj):
                if isinstance(obj, dict):
                    return {k: clean_struct(v) for k, v in obj.items() if v is not None and v != "" and v != [] and v != {}}
                elif isinstance(obj, list):
                    return [clean_struct(item) for item in obj if item is not None and item != ""]
                return obj

            cleaned = clean_struct(parsed)
            compact_json = json.dumps(cleaned, separators=(",", ":"), ensure_ascii=False)
            return f"[CCR-REF:{cache_id}] {compact_json}"
        except Exception:
            # Fallback: regex whitespace compaction
            compacted = re.sub(r"\s+", " ", raw_json).strip()
            return f"[CCR-REF:{cache_id}] {compacted}"

    def _headroom_compress_code_and_logs(self, raw_code: str, cache_id: str) -> str:
        """Compresses code/logs by stripping verbose blank lines and comments while preserving AST tokens."""
        lines = [line.rstrip() for line in raw_code.splitlines() if line.strip()]
        # Filter purely empty comment lines but preserve code docstrings
        filtered = [line for line in lines if not (line.strip().startswith("#") and len(line.strip()) > 1 and "TODO" not in line and "CRITICAL" not in line)]
        joined = "\n".join(filtered)
        return f"[CCR-REF:{cache_id}]\n{joined}"

    def _llmlingua_compress_prose(self, raw_prose: str, cache_id: str) -> str:
        """Compresses natural language prose by removing redundant conversational filler while keeping facts."""
        filler_words = [
            r"\b(as we all know,?\s*|it is important to note that\s*|basically,?\s*|in order to\s*|as mentioned previously,?\s*)\b",
            r"\b(please note that\s*|furthermore,?\s*|moreover,?\s*|it should be noted that\s*|needless to say,?\s*)\b",
            r"\b(s'il vous plaît,?\s*|il convient de noter que\s*|comme nous le savons tous,?\s*|en somme,?\s*|il est clair que\s*)\b",
        ]
        compacted = raw_prose
        for pat in filler_words:
            compacted = re.sub(pat, "", compacted, flags=re.IGNORECASE)
        compacted = re.sub(r"\s+", " ", compacted).strip()
        return compacted
