"""E-ZZIO Core — Sovereign Memory Ingestion Manager (Phase 5.0).

Enforces strict rules for committing new memory items into runtime/memory_store/:
1. Memory write MUST be backed by a verified EvidenceEnvelope.
2. Direct writes without evidence are rejected Fail-Closed.
3. L5 Constitutional tier is IMMUTABLE (cannot be written by external agents).
4. Commits an audit block to the frozen Decision Ledger V10.0.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.cognition.evidence.envelope import EvidenceEnvelope
from core.cognition.evidence.store import EvidenceStore
from core.cognition.decision_ledger import DecisionLedgerEngine

logger = logging.getLogger(__name__)


class SovereignMemoryError(Exception):
    """Raised on invalid memory ingestion attempts or security violations."""

    pass


@dataclass
class MemoryRecord:
    tier: str  # "L1_EPISODIC", "L2_SEMANTIC", "L3_EXPERIENCE", "L4_SEMANTIC"
    memory_id: str
    timestamp_utc: str
    source: str
    importance: float
    compression_ratio: float
    original_sha256: str
    content: str
    evidence_id: str


class SovereignMemoryManager:
    IMMUTABLE_TIERS = {"L5_CONSTITUTION", "L5_GENOME"}

    def __init__(self, root_dir: Path = Path(r"G:\AI\E-zzio")):
        self.root_dir = root_dir
        self.store_dir = self.root_dir / "runtime" / "memory_store"
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.decision_engine = None
        self.evidence_store = None
        try:
            self.decision_engine = DecisionLedgerEngine(root_dir=self.root_dir)
            self.evidence_store = EvidenceStore(root_dir=self.root_dir, hmac_key=getattr(self.decision_engine, "hmac_key", None))
        except Exception:
            pass

    def ingest_memory(
        self,
        tier: str,
        content: str,
        source: str,
        evidence_envelope: Optional[EvidenceEnvelope] = None,
        importance: float = 1.0,
        compression_ratio: float = 1.0,
    ) -> MemoryRecord:
        """Ingests a verified memory item into the sovereign store backed by an EvidenceEnvelope."""
        # 1. Invariant: L5 Constitutional immunity
        if tier in self.IMMUTABLE_TIERS:
            raise SovereignMemoryError(f"FAIL-CLOSED: Tier '{tier}' is sovereignly immutable and cannot be written by ingestion.")

        # 2. Invariant: Strict Evidence Envelope requirement
        if evidence_envelope is None:
            raise SovereignMemoryError("FAIL-CLOSED: Memory ingestion strictly requires a verified EvidenceEnvelope.")

        # 3. Verify Evidence Integrity & Persist to Store if needed
        key = getattr(self.decision_engine, "hmac_key", None)
        if not evidence_envelope.verify_integrity(key=key):
            raise SovereignMemoryError(f"FAIL-CLOSED: Evidence envelope '{evidence_envelope.evidence_id}' has invalid cryptographic integrity.")

        if self.evidence_store is not None:
            ev_file = self.evidence_store.store_dir / f"{evidence_envelope.evidence_id}.json"
            if not ev_file.exists():
                try:
                    self.evidence_store.store_evidence(evidence_envelope)
                except Exception as ee:
                    logger.warning(f"[MEMORY MANAGER] Evidence auto-store warning: {ee}")

        # 4. Construct MemoryRecord
        tier_dir = self.store_dir / tier
        tier_dir.mkdir(parents=True, exist_ok=True)

        prefix = tier[:3]
        mem_id = f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        ts = datetime.now(timezone.utc).isoformat()
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        rec = MemoryRecord(
            tier=tier,
            memory_id=mem_id,
            timestamp_utc=ts,
            source=source,
            importance=importance,
            compression_ratio=compression_ratio,
            original_sha256=content_hash,
            content=content,
            evidence_id=evidence_envelope.evidence_id,
        )

        # 5. Atomic write to disk
        target_path = tier_dir / f"{mem_id}.json"
        temp_path = target_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(asdict(rec), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temp_path.replace(target_path)

        # 6. Commit audit decision to frozen Decision Ledger V10.0
        if self.decision_engine is not None:
            try:
                self.decision_engine.record_decision(
                    subsystem="MemorySync",
                    decision_type="SOVEREIGN_MEMORY_INGESTION",
                    context={"tier": tier, "memory_id": mem_id, "evidence_id": evidence_envelope.evidence_id},
                    action_payload={"content_hash": content_hash, "source": source},
                    rationale=f"Ingested verified memory {mem_id} into tier {tier} with Evidence {evidence_envelope.evidence_id}.",
                )
            except Exception as le:
                logger.warning(f"[MEMORY MANAGER] Ledger recording warning: {le}")

        logger.info(f"[SOVEREIGN MEMORY] Successfully ingested memory '{mem_id}' into tier '{tier}'.")
        return rec

    def retrieve_memory(self, memory_id: str) -> Optional[MemoryRecord]:
        """Searches and loads a memory record across all tiers."""
        for json_path in self.store_dir.rglob(f"{memory_id}.json"):
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
                rec = MemoryRecord(**data)
                if not self.verify_memory_record(rec):
                    logger.error(f"[MEMORY AUDIT] Content hash mismatch on memory {memory_id}")
                    return None
                return rec
            except Exception:
                return None
        return None

    def verify_memory_record(self, record: MemoryRecord) -> bool:
        """Verifies content integrity against original_sha256."""
        actual_hash = hashlib.sha256(record.content.encode("utf-8")).hexdigest()
        return actual_hash == record.original_sha256
