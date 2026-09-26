"""
core/orchestration/worker_lease.py — Sovereign Worker Lease & Ownership Manager (OpenMuse adaptation).

Guarantees mutually exclusive worker ownership per task:
- Prevents concurrent execution of the same unit of work by multiple workers
- TTL-based leases with heartbeat renewal
- Automatic recovery of stale/expired leases
- Rejection of unauthorized takeover while lease is active
- Preserves MissionRegistry as sole mission state authority (leases are operational locks).
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("WorkerLeaseManager")


@dataclass
class WorkerLease:
    lease_id: str
    task_id: str
    owner_id: str
    acquired_at: float
    expires_at: float
    ttl_seconds: float

    def is_valid(self, now: float | None = None) -> bool:
        current = now if now is not None else time.time()
        return current < self.expires_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "lease_id": self.lease_id,
            "task_id": self.task_id,
            "owner_id": self.owner_id,
            "acquired_at": self.acquired_at,
            "expires_at": self.expires_at,
            "ttl_seconds": self.ttl_seconds,
            "is_valid": self.is_valid(),
        }


class WorkerLeaseManager:
    """Gestionnaire de baux (leases) thread-safe pour les workers de tâches."""

    def __init__(self) -> None:
        self._leases: dict[str, WorkerLease] = {}  # task_id -> WorkerLease
        self._lock = threading.Lock()

    def acquire_lease(
        self,
        task_id: str,
        owner_id: str,
        ttl_seconds: float = 30.0,
    ) -> tuple[bool, WorkerLease | None, str]:
        """
        Tente d'acquérir un bail exclusif sur une tâche.
        Retourne (success, lease, reason).
        """
        now = time.time()
        with self._lock:
            existing = self._leases.get(task_id)

            # Cas 1: Pas de bail existant
            if existing is None:
                lease = WorkerLease(
                    lease_id=f"lease_{uuid.uuid4().hex[:12]}",
                    task_id=task_id,
                    owner_id=owner_id,
                    acquired_at=now,
                    expires_at=now + ttl_seconds,
                    ttl_seconds=ttl_seconds,
                )
                self._leases[task_id] = lease
                return True, lease, "LEASE_ACQUIRED"

            # Cas 2: Bail expiré (stale lease recoverable)
            if not existing.is_valid(now):
                new_lease = WorkerLease(
                    lease_id=f"lease_{uuid.uuid4().hex[:12]}",
                    task_id=task_id,
                    owner_id=owner_id,
                    acquired_at=now,
                    expires_at=now + ttl_seconds,
                    ttl_seconds=ttl_seconds,
                )
                self._leases[task_id] = new_lease
                return True, new_lease, f"STALE_LEASE_RECOVERED_FROM_{existing.owner_id}"

            # Cas 3: Même propriétaire -> Renouvellement
            if existing.owner_id == owner_id:
                existing.expires_at = now + ttl_seconds
                existing.ttl_seconds = ttl_seconds
                return True, existing, "LEASE_RENEWED"

            # Cas 4: Bail actif détenu par un autre worker -> Refus formel
            return False, existing, f"LEASE_DENIED_ACTIVE_OWNER_{existing.owner_id}"

    def renew_lease(
        self,
        lease_id: str,
        owner_id: str,
        additional_seconds: float = 30.0,
    ) -> bool:
        """Renouvelle un bail actif si l'owner_id correspond."""
        now = time.time()
        with self._lock:
            for _task_id, lease in self._leases.items():
                if lease.lease_id == lease_id:
                    if lease.owner_id != owner_id:
                        return False
                    if not lease.is_valid(now):
                        return False
                    lease.expires_at = now + additional_seconds
                    return True
        return False

    def release_lease(self, lease_id: str, owner_id: str) -> bool:
        """Libère explicitement un bail détenu."""
        with self._lock:
            for task_id, lease in list(self._leases.items()):
                if lease.lease_id == lease_id:
                    if lease.owner_id == owner_id:
                        del self._leases[task_id]
                        return True
                    return False
        return False

    def is_lease_valid(self, task_id: str, owner_id: str) -> bool:
        """Vérifie si un worker détient un bail valide sur une tâche."""
        now = time.time()
        with self._lock:
            lease = self._leases.get(task_id)
            if lease is None:
                return False
            return lease.owner_id == owner_id and lease.is_valid(now)

    def recover_stale_leases(self, now: float | None = None) -> list[str]:
        """Purge les baux expirés et retourne la liste des task_ids libérés."""
        current = now if now is not None else time.time()
        recovered: list[str] = []
        with self._lock:
            for task_id, lease in list(self._leases.items()):
                if not lease.is_valid(current):
                    del self._leases[task_id]
                    recovered.append(task_id)
        return recovered
