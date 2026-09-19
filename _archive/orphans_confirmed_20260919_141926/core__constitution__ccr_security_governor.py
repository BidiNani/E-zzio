"""E-ZZIO Core — CCR Security Governor & Cache Authorization Gate (Phase 8.5).

Guarantees that the CCR (Compress-Cache-Retrieve) cache store (runtime/compression_cache/)
cannot be used as a shadow backdoor to bypass ContextFabric sanitization, constitutional rules,
or secret redaction filters.
Enforces:
1. Role-based and Policy-gated retrieval authorization.
2. Cryptographic SHA-256 payload integrity verification on every cache read.
3. Secret and PII redaction pass on retrieved raw content before delivery to downstream models.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(r"G:\AI\E-zzio")

from core.cognition.decision_ledger import DecisionLedgerEngine
from core.cognition.memory.context_fabric import ContextFabric

logger = logging.getLogger(__name__)


@dataclass
class CCRRetrievalVerdict:
    cache_id: str
    is_authorized: bool
    retrieval_status: str  # "AUTHORIZED_SANITIZED", "SECURITY_VETO_UNAUTHORIZED", "INTEGRITY_TAMPER_FAIL"
    effective_content: str | None
    rationale: str
    timestamp_utc: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class CCRSecurityGovernor:
    def __init__(self, root_dir: Path = ROOT_DIR):
        self.root_dir = root_dir
        self.cache_dir = self.root_dir / "runtime" / "compression_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.fabric = ContextFabric(root_dir=self.root_dir)
        self.decision_engine = None
        try:
            self.decision_engine = DecisionLedgerEngine(root_dir=self.root_dir)
        except Exception:
            pass

    def authorize_and_retrieve(
        self,
        task_id: str,
        cache_id: str,
        requesting_provider: str,
        requesting_capability: str,
        authorization_ticket: dict[str, Any] | None = None,
    ) -> CCRRetrievalVerdict:
        """
        Sovereign authorization gate for CCR raw content retrieval.
        Direct, unvetted access by LLM or subagent is strictly prohibited.
        """
        # 1. Authorization Policy Check: Must have a valid routing ticket from Cognitive Router
        if not authorization_ticket or authorization_ticket.get("policy_clearance") != "APPROVED_BY_ROUTER":
            logger.error(f"[CCR SECURITY] Unauthorized direct retrieval attempt for {cache_id} by {requesting_provider}.")
            return self._record_verdict(
                task_id=task_id,
                cache_id=cache_id,
                authorized=False,
                status="SECURITY_VETO_UNAUTHORIZED",
                content=None,
                rationale=f"SECURITY VETO: Direct CCR access prohibited for provider '{requesting_provider}'. Missing router clearance ticket.",
            )

        cache_file = self.cache_dir / f"{cache_id}.json"
        if not cache_file.exists():
            return self._record_verdict(
                task_id=task_id,
                cache_id=cache_id,
                authorized=False,
                status="CACHE_MISS_NOT_FOUND",
                content=None,
                rationale=f"CCR cache entry '{cache_id}' not found on disk.",
            )

        # 2. Cryptographic Integrity Check on Disk Artifact
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            expected_sha = data.get("sha256")
            raw_text = data.get("original_text", "")

            actual_sha = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
            if actual_sha != expected_sha:
                logger.error(f"[CCR SECURITY] Tampering detected in CCR cache {cache_id}! Expected {expected_sha}, got {actual_sha}.")
                return self._record_verdict(
                    task_id=task_id,
                    cache_id=cache_id,
                    authorized=False,
                    status="INTEGRITY_TAMPER_FAIL",
                    content=None,
                    rationale=f"FAIL-CLOSED: Cache payload SHA-256 mismatch for {cache_id}. Possible disk corruption or tampering.",
                )
        except Exception as e:
            return self._record_verdict(
                task_id=task_id,
                cache_id=cache_id,
                authorized=False,
                status="CORRUPTED_CACHE_JSON",
                content=None,
                rationale=f"Could not parse CCR cache JSON: {e}",
            )

        # 3. Secret & PII Redaction Pass via ContextFabric Sanitizer
        sanitized_text = self.fabric._sanitize_memory_content(raw_text)

        # Redact API keys and raw tokens
        secret_patterns = [
            r"AIzaSy[A-Za-z0-9_-]{10,}",
            r"gsk_[A-Za-z0-9_-]{10,}",
            r"sk-[A-Za-z0-9_-]{10,}",
        ]
        for sp in secret_patterns:
            sanitized_text = re.sub(sp, "[REDACTED_SECRET]", sanitized_text)

        return self._record_verdict(
            task_id=task_id,
            cache_id=cache_id,
            authorized=True,
            status="AUTHORIZED_SANITIZED",
            content=sanitized_text,
            rationale="CCR access authorized via Cognitive Router; raw payload cryptographically verified and sanitized.",
        )

    def _record_verdict(
        self,
        task_id: str,
        cache_id: str,
        authorized: bool,
        status: str,
        content: str | None,
        rationale: str,
    ) -> CCRRetrievalVerdict:
        v = CCRRetrievalVerdict(
            cache_id=cache_id,
            is_authorized=authorized,
            retrieval_status=status,
            effective_content=content,
            rationale=rationale,
        )

        if self.decision_engine:
            try:
                self.decision_engine.record_decision(
                    subsystem="CCRSecurityGovernor",
                    decision_type=f"CCR_{status}",
                    context={"task_id": task_id, "cache_id": cache_id, "is_authorized": authorized},
                    action_payload={"payload_delivered": content is not None, "length": len(content) if content else 0},
                    rationale=rationale,
                )
            except Exception as le:
                logger.warning(f"[CCR SECURITY GOVERNOR] Ledger recording warning: {le}")

        return v
