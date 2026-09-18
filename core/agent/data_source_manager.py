"""
core/agent/data_source_manager.py — Data Source Manager & Security Boundary for Structured Data Access.
Hierarchy: LOCAL_SQLITE -> LOCAL_FILE -> OPEN_DATA_API -> PUBLIC_FREE_API -> FREE_TIER_CLOUD -> PAID_CLOUD.
"""
from __future__ import annotations

import logging
import os
import sqlite3
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("ezzio.agent.data_source_manager")


class DataSourceType(str, Enum):
    LOCAL_SQLITE = "LOCAL_SQLITE"
    LOCAL_FILE = "LOCAL_FILE"
    OPEN_DATA_API = "OPEN_DATA_API"
    PUBLIC_FREE_API = "PUBLIC_FREE_API"
    FREE_TIER_CLOUD = "FREE_TIER_CLOUD"
    PAID_CLOUD = "PAID_CLOUD"


# Ordre de priorité des sources : le local et le gratuit priment toujours
SOURCE_PRIORITY_ORDER = [
    DataSourceType.LOCAL_SQLITE,
    DataSourceType.LOCAL_FILE,
    DataSourceType.OPEN_DATA_API,
    DataSourceType.PUBLIC_FREE_API,
    DataSourceType.FREE_TIER_CLOUD,
    DataSourceType.PAID_CLOUD,
]


@dataclass
class DataSourceRecord:
    source_id: str
    name: str
    source_type: DataSourceType
    location: str  # Chemin de fichier ou URL API
    read_only: bool = True
    rate_limit_per_min: int | None = None
    license_type: str = "open"
    metadata: dict[str, Any] = field(default_factory=dict)


class DataSourceManager:
    """Gestionnaire de sources de données : découverte, sélection par priorité, requêtes paramétrées et traçabilité."""

    def __init__(self, workspace_root: str | None = None):
        self.workspace_root = workspace_root or r"G:\AI\E-zzio"
        self._sources: dict[str, DataSourceRecord] = {}
        self._register_default_local_sources()

    def _register_default_local_sources(self) -> None:
        """Enregistre les bases SQLite et fichiers de données locaux connus du projet."""
        evidence_db = os.path.join(self.workspace_root, "runtime", "evidence", "evidence.db")
        audit_db = os.path.join(self.workspace_root, "runtime", "evidence", "audit_ledger.db")

        if os.path.exists(evidence_db):
            self.register_source(DataSourceRecord(
                source_id="local_evidence_db",
                name="Evidence Database (SQLite)",
                source_type=DataSourceType.LOCAL_SQLITE,
                location=evidence_db,
                read_only=True
            ))

        if os.path.exists(audit_db):
            self.register_source(DataSourceRecord(
                source_id="local_audit_db",
                name="Audit Ledger Database (SQLite)",
                source_type=DataSourceType.LOCAL_SQLITE,
                location=audit_db,
                read_only=True
            ))

    def register_source(self, record: DataSourceRecord) -> None:
        """Enregistre une source de données dans le manager."""
        self._sources[record.source_id] = record
        logger.info("[DATA-SOURCE] Source enregistrée : '%s' (%s)", record.source_id, record.source_type.value)

    def discover_best_source(self, required_type: DataSourceType | None = None) -> DataSourceRecord | None:
        """Sélectionne la source disponible la plus prioritaire selon la hiérarchie économique."""
        if not self._sources:
            return None

        # Tri selon l'ordre de priorité strict
        for s_type in SOURCE_PRIORITY_ORDER:
            if required_type and s_type != required_type:
                continue
            for src in self._sources.values():
                if src.source_type == s_type:
                    return src
        return list(self._sources.values())[0]

    def execute_parameterized_sql(
        self,
        source_id: str,
        sql_query: str,
        params: tuple[Any, ...] | dict[str, Any] = (),
        is_write: bool = False,
        agent_permissions: list[str] | None = None
    ) -> dict[str, Any]:
        """Exécute de manière sécurisée une requête SQL paramétrée contre une base SQLite locale."""
        src = self._sources.get(source_id)
        if not src:
            return {"ok": False, "error": f"Source de données introuvable : {source_id}"}

        if src.source_type != DataSourceType.LOCAL_SQLITE:
            return {"ok": False, "error": f"La source {source_id} n'est pas une base SQL locale."}

        # 1. Vérification des permissions agent
        perms = agent_permissions or ["database.read"]
        if is_write and "database.write" not in perms:
            self._log_audit("DATA_ACCESS_DENIED", {"source_id": source_id, "reason": "database.write permission required"})
            return {"ok": False, "error": "PERMISSION_DENIED: database.write est requis pour les opérations d'écriture."}

        # 2. Protection contre les DDL destructifs
        query_upper = sql_query.strip().upper()
        if any(keyword in query_upper for keyword in ["DROP TABLE", "ALTER TABLE", "TRUNCATE"]):
            return {"ok": False, "error": "SECURITY_BLOCK: Les commandes DDL destructives sont interdites."}

        if src.read_only and is_write:
            return {"ok": False, "error": "READ_ONLY_VIOLATION: La source est configurée en lecture seule."}

        # 3. Exécution paramétrée sécurisée
        try:
            conn = sqlite3.connect(src.location, timeout=10.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql_query, params)

            if is_write:
                conn.commit()
                rows_affected = cursor.rowcount
                conn.close()
                self._record_provenance(source_id, sql_query, rows_affected, "write")
                return {"ok": True, "rows_affected": rows_affected}
            else:
                rows = [dict(row) for row in cursor.fetchall()]
                conn.close()
                self._record_provenance(source_id, sql_query, len(rows), "read")
                return {"ok": True, "rows": rows, "count": len(rows)}
        except Exception as exc:
            logger.error("[DATA-SQL-ERROR] Erreur exécution SQL sur %s : %s", source_id, exc)
            return {"ok": False, "error": str(exc)}

    def _record_provenance(self, source_id: str, query_summary: str, record_count: int, access_type: str) -> None:
        """Consigne la provenance et l'accès aux données dans l'AuditLedger."""
        payload = {
            "source_id": source_id,
            "access_type": access_type,
            "query_summary": query_summary[:200],
            "record_count": record_count,
        }
        self._log_audit("DATA_PROVENANCE_RECORDED", payload)

    def _log_audit(self, action: str, payload: dict[str, Any]) -> None:
        """Méthode interne pour inscrire des événements d'audit."""
        try:
            from core.security.audit_ledger import AuditLedger
            AuditLedger().record_event(actor="data-source-manager", action=action, payload=payload)
        except Exception as exc:
            logger.warning("[DATA-AUDIT] Audit non enregistré : %s", exc)


data_source_manager = DataSourceManager()
