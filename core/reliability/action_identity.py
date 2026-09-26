"""
core/reliability/action_identity.py — Sovereign Action Identity & Canonical Proposal (OpenMuse adaptation).

Binds external mutations to deterministic, immutable identities:
- Canonical JSON serialization (sorted keys, compact delimiters)
- SHA-256 payload hash
- Stable operation_id = f"op_{payload_hash[:16]}"
- Detects duplicate dispatches and invalidates approvals when payloads are modified.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def canonical_json(data: dict[str, Any]) -> str:
    """Génère une représentation JSON canonique déterministe (clés triées, sans espace superflu)."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_payload_hash(payload: dict[str, Any]) -> str:
    """Calcule l'empreinte SHA-256 du JSON canonique."""
    c_json = canonical_json(payload)
    return hashlib.sha256(c_json.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ActionProposal:
    """Proposition d'action scellée cryptographiquement avec identité immuable."""

    operation_id: str
    mission_id: str
    task_id: str
    action_type: str
    payload: dict[str, Any]
    payload_hash: str
    is_external: bool = False
    is_idempotent: bool = False
    version: int = 1
    created_at: str = field(default_factory=utc_now)
    correlation_id: str = field(default_factory=lambda: f"corr_{uuid.uuid4().hex[:12]}")

    @classmethod
    def create(
        cls,
        mission_id: str,
        task_id: str,
        action_type: str,
        payload: dict[str, Any],
        is_external: bool = False,
        is_idempotent: bool = False,
        version: int = 1,
        correlation_id: str | None = None,
    ) -> ActionProposal:
        p_hash = compute_payload_hash(payload)
        op_id = f"op_{p_hash[:16]}"
        return cls(
            operation_id=op_id,
            mission_id=mission_id,
            task_id=task_id,
            action_type=action_type,
            payload=payload,
            payload_hash=p_hash,
            is_external=is_external,
            is_idempotent=is_idempotent,
            version=version,
            created_at=utc_now(),
            correlation_id=correlation_id or f"corr_{uuid.uuid4().hex[:12]}",
        )

    def verify_payload_match(self, candidate_payload: dict[str, Any]) -> bool:
        """Vérifie si le payload candidat correspond exactement au hash scellé."""
        return compute_payload_hash(candidate_payload) == self.payload_hash

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "mission_id": self.mission_id,
            "task_id": self.task_id,
            "action_type": self.action_type,
            "payload": self.payload,
            "payload_hash": self.payload_hash,
            "is_external": self.is_external,
            "is_idempotent": self.is_idempotent,
            "version": self.version,
            "created_at": self.created_at,
            "correlation_id": self.correlation_id,
        }


class ActionDispatchRegistry:
    """Registre de détection des dispatches dupliqués pour effets externes."""

    def __init__(self) -> None:
        self._dispatched: dict[str, dict[str, Any]] = {}

    def register_dispatch(self, proposal: ActionProposal) -> tuple[bool, str]:
        """
        Enregistre une intention de dispatch.
        Retourne (True, 'DISPATCH_ACCEPTED') si première tentative,
        ou (False, 'DUPLICATE_DISPATCH_DETECTED') si l'opération a déjà été engagée avec le même hash.
        """
        op_id = proposal.operation_id
        if op_id in self._dispatched:
            existing = self._dispatched[op_id]
            if existing["payload_hash"] == proposal.payload_hash:
                return False, f"DUPLICATE_DISPATCH_DETECTED:{op_id}"

        self._dispatched[op_id] = {
            "operation_id": op_id,
            "task_id": proposal.task_id,
            "mission_id": proposal.mission_id,
            "payload_hash": proposal.payload_hash,
            "dispatched_at": utc_now(),
            "status": "DISPATCHED",
        }
        return True, "DISPATCH_ACCEPTED"

    def mark_completed(self, operation_id: str, result: dict[str, Any] | None = None) -> None:
        if operation_id in self._dispatched:
            self._dispatched[operation_id]["status"] = "COMPLETED"
            self._dispatched[operation_id]["result"] = result or {}

    def is_dispatched(self, operation_id: str) -> bool:
        return operation_id in self._dispatched

    def get_dispatch_record(self, operation_id: str) -> dict[str, Any] | None:
        return self._dispatched.get(operation_id)
