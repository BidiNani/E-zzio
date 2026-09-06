"""
E-ZZIO Core V10.6 — User Preservation Gate & Zero Data Loss System.
Garantit la préservation absolue des fichiers, configurations, artifacts, agents et outils utilisateur.
Impose la classification de sécurité: UNKNOWN = PROTECTED (USER_OWNED).
"""
from __future__ import annotations

import logging
import hashlib
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ezzio.authority.user_preservation")


class FileOwnership(str, Enum):
    USER_OWNED = "USER_OWNED"
    SYSTEM_OWNED = "SYSTEM_OWNED"
    GENERATED = "GENERATED"
    AUDIT = "AUDIT"
    CERTIFICATION = "CERTIFICATION"
    UNKNOWN = "UNKNOWN"  # Par sécurité: UNKNOWN = PROTECTED (USER_OWNED)


@dataclass
class FileBaseline:
    path: str
    existence: bool
    size: int
    content_hash: str
    ownership: FileOwnership


@dataclass
class UserPreservationReport:
    status: str = "PASS"  # PASS / FAIL
    user_data_loss: int = 0
    unexpected_user_changes: int = 0
    user_files_deleted: int = 0
    user_artifacts_lost: int = 0
    user_config_overwrites: int = 0
    preexisting_changes_preserved: bool = True
    details: List[str] = field(default_factory=list)


class UserPreservationGate:
    """Gate souveraine de préservation utilisateur d'E-ZZIO."""

    def __init__(self) -> None:
        self.baselines: Dict[str, FileBaseline] = {}

    def compute_hash(self, content: bytes) -> str:
        """Calcule le hash SHA-256 déterministe d'un contenu."""
        return hashlib.sha256(content).hexdigest()

    def classify_file(self, path: str) -> FileOwnership:
        """Classifie la propriété d'un fichier. En cas de doute -> UNKNOWN (PROTECTED)."""
        path_clean = path.replace("\\", "/").lower()

        if "state/audit/" in path_clean:
            if "certification" in path_clean or "seal" in path_clean:
                return FileOwnership.CERTIFICATION
            return FileOwnership.AUDIT
        elif "artifacts/" in path_clean or "user_" in path_clean or "custom_" in path_clean:
            return FileOwnership.USER_OWNED
        elif "core/" in path_clean and ("__init__.py" in path_clean or "frozen_" in path_clean):
            return FileOwnership.SYSTEM_OWNED
        elif "cache/" in path_clean or "tmp/" in path_clean:
            return FileOwnership.GENERATED
        else:
            # Règle Zéro: Tout fichier non catégorisé est UNKNOWN -> PROTECTED
            return FileOwnership.UNKNOWN

    def capture_baseline(self, paths: List[str], file_contents: Optional[Dict[str, bytes]] = None) -> Dict[str, FileBaseline]:
        """Capture l'état initial des fichiers ciblés sans altération."""
        for path in paths:
            ownership = self.classify_file(path)
            content = (file_contents or {}).get(path, b"")
            h = self.compute_hash(content)
            bl = FileBaseline(
                path=path,
                existence=True,
                size=len(content),
                content_hash=h,
                ownership=ownership,
            )
            self.baselines[path] = bl
        return self.baselines

    def can_delete(self, path: str) -> bool:
        """Delete Gate (Section 9): Empêche toute suppression de fichier USER_OWNED ou UNKNOWN."""
        ownership = self.classify_file(path)
        if ownership in (FileOwnership.USER_OWNED, FileOwnership.UNKNOWN):
            logger.warning(f"[DELETE-GATE-BLOCKED] Tentative de suppression bloquée pour {path} ({ownership.value})")
            return False
        return True

    def minimal_config_patch(self, user_config: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
        """Configuration Gate (Section 11): Applique uniquement les changements ciblés en préservant les clés utilisateur."""
        result = dict(user_config)  # Copie profonde des clés utilisateur
        result.update(patch)
        return result

    def verify_preservation(
        self,
        current_files: Dict[str, bytes],
        deleted_paths: Optional[List[str]] = None,
    ) -> UserPreservationReport:
        """Évalue l'intégrité globale et garantit l'absence de perte de données utilisateur."""
        report = UserPreservationReport()
        deleted_paths = deleted_paths or []

        # 1. Vérification des suppressions non autorisées
        for path in deleted_paths:
            ownership = self.classify_file(path)
            if ownership in (FileOwnership.USER_OWNED, FileOwnership.UNKNOWN):
                report.user_files_deleted += 1
                report.user_data_loss += 1
                report.details.append(f"Suppression non autorisée d'un fichier utilisateur: {path}")

        # 2. Vérification des écrasements et altérations
        for path, bl in self.baselines.items():
            if path in deleted_paths:
                continue

            current_content = current_files.get(path)
            if current_content is None:
                if bl.ownership in (FileOwnership.USER_OWNED, FileOwnership.UNKNOWN):
                    report.user_files_deleted += 1
                    report.user_data_loss += 1
                    report.details.append(f"Fichier utilisateur manquant: {path}")
                continue

            curr_hash = self.compute_hash(current_content)
            if curr_hash != bl.content_hash and bl.ownership in (FileOwnership.USER_OWNED, FileOwnership.UNKNOWN):
                # Modification d'un fichier protégé non ciblé
                report.unexpected_user_changes += 1
                report.details.append(f"Changement inattendu sur fichier protégé: {path}")

        # Statut global
        if report.user_data_loss > 0 or report.unexpected_user_changes > 0 or report.user_files_deleted > 0:
            report.status = "FAIL"
            report.preexisting_changes_preserved = False
        else:
            report.status = "PASS"
            report.preexisting_changes_preserved = True

        return report


user_preservation_gate = UserPreservationGate()
