"""core/capabilities/operational_helper.py — Utilitaire opérationnel de télémétrie pour E-ZZIO."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any


def compute_task_checksum(task_id: str, payload: dict[str, Any] | None = None) -> str:
    """Calcule une empreinte SHA-256 tronquée à 16 caractères pour la tâche et son payload."""
    raw_payload = json.dumps(payload or {}, sort_keys=True, ensure_ascii=False)
    raw_str = f"{task_id}:{raw_payload}"
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()[:16]


def format_task_receipt(task_id: str, status: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Génère un reçu de tâche structuré et scellé."""
    checksum = compute_task_checksum(task_id, payload)
    return {
        "task_id": task_id,
        "status": status.upper(),
        "checksum": checksum,
        "timestamp_utc": datetime.now(UTC).isoformat(),
    }
