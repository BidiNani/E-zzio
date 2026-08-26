"""E-ZZIO Core — Federated Evidence & Provenance Envelope (Phase 4.2).

Defines the cryptographic EvidenceEnvelope structure ensuring 100% forensic attestation
for all local, cloud, and agentic intelligence outputs before ingestion by E-ZZIO.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class EvidenceEnvelope:
    evidence_id: str
    task_id: str
    timestamp_utc: str
    provider: str  # "local_ollama", "cloud_gemini", "agent_antigravity"
    model_name: str
    agent_version: str
    capability: str
    policy_status: str  # "APPROVED", "RESTRICTED", "QUARANTINED"
    input_context_hash: str
    output_payload_hash: str
    execution_duration_ms: float
    verification_status: str = "VERIFIED_VALID"
    raw_payload_snippet: str = ""
    ledger_decision_id: Optional[str] = None
    envelope_signature_hmac: Optional[str] = None

    @classmethod
    def create(
        cls,
        task_id: str,
        provider: str,
        model_name: str,
        capability: str,
        input_prompt: str,
        output_payload: str,
        execution_duration_ms: float,
        policy_status: str = "APPROVED",
        agent_version: str = "ezzio-federated-v1.0",
        ledger_decision_id: Optional[str] = None,
        signing_key: Optional[bytes] = None,
    ) -> EvidenceEnvelope:
        """Constructs and cryptographically seals an EvidenceEnvelope."""
        ts = datetime.now(timezone.utc).isoformat()
        evidence_id = f"EVID-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

        in_hash = hashlib.sha256(input_prompt.encode("utf-8")).hexdigest()
        out_hash = hashlib.sha256(output_payload.encode("utf-8")).hexdigest()

        snippet = output_payload[:200] if len(output_payload) > 200 else output_payload

        envelope = cls(
            evidence_id=evidence_id,
            task_id=task_id,
            timestamp_utc=ts,
            provider=provider,
            model_name=model_name,
            agent_version=agent_version,
            capability=capability,
            policy_status=policy_status,
            input_context_hash=in_hash,
            output_payload_hash=out_hash,
            execution_duration_ms=execution_duration_ms,
            verification_status="VERIFIED_VALID",
            raw_payload_snippet=snippet,
            ledger_decision_id=ledger_decision_id,
        )

        if signing_key:
            envelope.seal(signing_key)

        return envelope

    def seal(self, key: bytes) -> None:
        """Applies SHA-256 HMAC signature over canonical envelope representation."""
        unsigned = {k: v for k, v in asdict(self).items() if k != "envelope_signature_hmac"}
        canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        self.envelope_signature_hmac = hmac.new(key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()

    def verify_integrity(self, key: Optional[bytes] = None, raw_output: Optional[str] = None, raw_prompt: Optional[str] = None) -> bool:
        """Verifies payload hash matching and cryptographic signature."""
        if raw_prompt is not None:
            actual_in_hash = hashlib.sha256(raw_prompt.encode("utf-8")).hexdigest()
            if actual_in_hash != self.input_context_hash:
                return False

        if raw_output is not None:
            actual_out_hash = hashlib.sha256(raw_output.encode("utf-8")).hexdigest()
            if actual_out_hash != self.output_payload_hash:
                return False

        if key and self.envelope_signature_hmac:
            unsigned = {k: v for k, v in asdict(self).items() if k != "envelope_signature_hmac"}
            canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            expected_sig = hmac.new(key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected_sig, self.envelope_signature_hmac):
                return False

        return True

    def verify_ledger_confrontation(self, ledger_record: Dict[str, Any]) -> bool:
        """Confronts envelope metadata against the ground-truth frozen Decision Ledger block."""
        if not ledger_record:
            return False

        rec_evidence_id = ledger_record.get("context", {}).get("evidence_id")
        rec_decision_id = ledger_record.get("decision_id")

        if rec_evidence_id != self.evidence_id:
            return False

        if self.ledger_decision_id and rec_decision_id != self.ledger_decision_id:
            return False

        return True
