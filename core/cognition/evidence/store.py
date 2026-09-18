"""E-ZZIO Core — Federated Evidence Store (Phase 4.2).

Persistent, query-time verified storage manager for EvidenceEnvelopes under runtime/evidence_store/.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path

from core.cognition.evidence.envelope import EvidenceEnvelope

logger = logging.getLogger(__name__)


class EvidenceStore:
    def __init__(self, root_dir: Path = Path(r"G:\AI\E-zzio"), hmac_key: bytes | None = None):
        self.root_dir = root_dir
        self.store_dir = self.root_dir / "runtime" / "evidence_store"
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.hmac_key = hmac_key

    def store_evidence(self, envelope: EvidenceEnvelope) -> Path:
        """Atomically persists an EvidenceEnvelope to disk."""
        file_name = f"{envelope.evidence_id}.json"
        target_path = self.store_dir / file_name

        data = asdict(envelope)
        temp_path = target_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temp_path.replace(target_path)
        return target_path

    def load_evidence(self, evidence_id: str, verify: bool = True) -> EvidenceEnvelope | None:
        """Loads and verifies an EvidenceEnvelope by ID."""
        target_path = self.store_dir / f"{evidence_id}.json"
        if not target_path.exists():
            return None

        try:
            raw = json.loads(target_path.read_text(encoding="utf-8"))
            envelope = EvidenceEnvelope(**raw)
            if verify and self.hmac_key:
                if not envelope.verify_integrity(key=self.hmac_key):
                    logger.error(f"[EVIDENCE AUDIT] Integrity failure for envelope {evidence_id}")
                    envelope.verification_status = "SIGNATURE_CORRUPTED"
            return envelope
        except Exception as e:
            logger.error(f"[EVIDENCE STORE] Failed loading envelope {evidence_id}: {e}")
            return None

    def list_all_evidence_ids(self) -> list[str]:
        """Returns all persisted evidence IDs."""
        return [p.stem for p in self.store_dir.glob("*.json")]
