"""
E-ZZIO Core V9.2 — Sovereign Artifact Provenance Engine.
Assure la traçabilité cryptographique absolue (SHA-256) de chaque fichier produit,
scellé avec la tâche créatrice, l'agent responsable, la décision de politique et l'audit.
"""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.security.audit_ledger import AuditLedger

logger = logging.getLogger("ArtifactProvenance")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ArtifactSeal:
    artifact_id: str
    file_path: str
    sha256: str
    size_bytes: int
    task_id: str
    agent_id: str
    action_type: str
    policy_decision: str
    correlation_id: str
    created_at: str
    parent_task_id: Optional[str] = None
    metadata_json: str = "{}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "file_path": self.file_path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "action_type": self.action_type,
            "policy_decision": self.policy_decision,
            "correlation_id": self.correlation_id,
            "created_at": self.created_at,
            "parent_task_id": self.parent_task_id,
            "metadata": json.loads(self.metadata_json),
        }


class ArtifactProvenanceEngine:
    """Moteur append-only scellant l'intégrité des artefacts générés."""

    def __init__(
        self,
        db_path: str = "runtime/evidence/artifact_provenance.db",
        audit_ledger: Optional[AuditLedger] = None,
    ):
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.audit_ledger = audit_ledger or AuditLedger()
        self._write_lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._write_lock:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS artifact_provenance (
                        artifact_id TEXT PRIMARY KEY,
                        file_path TEXT NOT NULL,
                        sha256 TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        task_id TEXT NOT NULL,
                        agent_id TEXT NOT NULL,
                        action_type TEXT NOT NULL,
                        policy_decision TEXT NOT NULL,
                        correlation_id TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        parent_task_id TEXT,
                        metadata_json TEXT NOT NULL
                    );
                """)
                # SQLite Trigger d'interdiction UPDATE / DELETE (append-only)
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS prevent_artifact_update
                    BEFORE UPDATE ON artifact_provenance
                    BEGIN
                        SELECT RAISE(FAIL, 'Artifact provenance entries are immutable');
                    END;
                """)
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS prevent_artifact_delete
                    BEFORE DELETE ON artifact_provenance
                    BEGIN
                        SELECT RAISE(FAIL, 'Artifact provenance entries cannot be deleted');
                    END;
                """)
                conn.commit()

    @staticmethod
    def compute_sha256(file_path: Path | str) -> str:
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"Artifact not found: {file_path}")
        h = hashlib.sha256()
        with open(p, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest().upper()

    def seal_artifact(
        self,
        file_path: Path | str,
        task_id: str,
        agent_id: str,
        action_type: str,
        policy_decision: str = "ALLOW",
        correlation_id: str = "",
        parent_task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        artifact_id: Optional[str] = None,
    ) -> ArtifactSeal:
        p = Path(file_path).resolve()
        sha256 = self.compute_sha256(p)
        size_bytes = p.stat().st_size
        art_id = artifact_id or f"art_{sha256[:12].lower()}"
        meta_json = json.dumps(metadata or {}, sort_keys=True)
        now = utc_now()

        seal = ArtifactSeal(
            artifact_id=art_id,
            file_path=str(p),
            sha256=sha256,
            size_bytes=size_bytes,
            task_id=task_id,
            agent_id=agent_id,
            action_type=action_type,
            policy_decision=policy_decision,
            correlation_id=correlation_id,
            created_at=now,
            parent_task_id=parent_task_id,
            metadata_json=meta_json,
        )

        with self._write_lock:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO artifact_provenance (
                        artifact_id, file_path, sha256, size_bytes, task_id,
                        agent_id, action_type, policy_decision, correlation_id,
                        created_at, parent_task_id, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    seal.artifact_id, seal.file_path, seal.sha256, seal.size_bytes,
                    seal.task_id, seal.agent_id, seal.action_type, seal.policy_decision,
                    seal.correlation_id, seal.created_at, seal.parent_task_id, seal.metadata_json
                ))
                conn.commit()

        # Audit append-only
        try:
            self.audit_ledger.record_event(
                actor=agent_id,
                action="ARTIFACT_SEALED",
                payload={
                    "artifact_id": seal.artifact_id,
                    "sha256": seal.sha256,
                    "file_path": seal.file_path,
                    "task_id": seal.task_id,
                    "policy": seal.policy_decision,
                },
                status="VERIFIED",
            )
        except Exception as e:
            logger.warning("Audit ledger recording failed for artifact: %s", e)

        return seal

    def verify_artifact(self, artifact_id: str) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM artifact_provenance WHERE artifact_id = ?", (artifact_id,))
            row = cur.fetchone()
            if not row:
                return {"verified": False, "error": f"Artifact '{artifact_id}' not found in provenance registry"}

            cols = [col[0] for col in cur.description]
            data = dict(zip(cols, row))

        current_file = Path(data["file_path"])
        if not current_file.exists():
            return {"verified": False, "error": f"Physical file missing: {data['file_path']}"}

        current_hash = self.compute_sha256(current_file)
        if current_hash != data["sha256"]:
            return {
                "verified": False,
                "error": "Tamper detected: SHA-256 mismatch",
                "expected_sha256": data["sha256"],
                "observed_sha256": current_hash,
            }

        return {
            "verified": True,
            "artifact_id": artifact_id,
            "file_path": data["file_path"],
            "sha256": current_hash,
            "task_id": data["task_id"],
            "agent_id": data["agent_id"],
            "sealed_at": data["created_at"],
        }

    def get_artifact(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """Récupère l'enregistrement scellé d'un artefact."""
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM artifact_provenance WHERE artifact_id = ?", (artifact_id,))
            row = cur.fetchone()
            if not row:
                return None
            cols = [col[0] for col in cur.description]
            res = dict(zip(cols, row))
            res["metadata"] = json.loads(res.get("metadata_json", "{}"))
            return res

    def list_task_artifacts(self, task_id: str) -> List[Dict[str, Any]]:
        """Récupère tous les artefacts scellés produits par une tâche ou ses sous-tâches."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT * FROM artifact_provenance WHERE task_id = ? OR parent_task_id = ? ORDER BY created_at ASC",
                (task_id, task_id),
            )
            cols = [col[0] for col in cur.description]
            artifacts = []
            for row in cur.fetchall():
                item = dict(zip(cols, row))
                item["metadata"] = json.loads(item.get("metadata_json", "{}"))
                artifacts.append(item)
            return artifacts


artifact_provenance = ArtifactProvenanceEngine()