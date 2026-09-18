"""Qualification des capacités externes — grilles pures, sans réseau, sans autorité.

Pipeline : SOURCE → INSPECT → SECURITY → LICENSE → DEPENDENCIES → VERDICT.
Un candidat externe démarre CANDIDATE et ne devient QUALIFIED qu'après
revue explicite. Le refus est définitif (REJECTED) ou borné (QUARANTINED).

Aucun fetch ici : le contenu distant est UNTRUSTED et qualifié sur ses
métadonnées + inspection locale, jamais sur sa réputation (stars/forks).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.capabilities.capability_qualification import QualificationStatus

# Licences compatibles avec une adoption (allowlist explicite).
LICENSE_ALLOWLIST = frozenset({"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "Unlicense"})

# Permissions qui imposent une revue humaine avant toute adoption.
SENSITIVE_PERMISSIONS = frozenset({
    "secret_access", "credential_access", "shell", "powershell",
    "arbitrary_filesystem_write", "process_spawn", "database_mutation",
    "self_modification", "network_unauthorized",
})

MAX_DEPENDENCIES = 5
MAX_CHAIN_DEPTH = 3


@dataclass
class ExternalCandidate:
    name: str
    source: str  # ex: github:owner/repo
    license: str | None = None
    permissions: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    has_tests: bool = False
    sandbox_verified: bool = False


@dataclass(frozen=True)
class QualificationVerdict:
    status: QualificationStatus
    reasons: list[str]
    escalation_level: int  # 2 = adoptable localement, 4 = revue humaine requise
    source: str = ""  # provenance conservée : quel candidat ce verdict juge


def qualify_external(candidate: ExternalCandidate) -> QualificationVerdict:
    """Applique les grilles dans l'ordre, premier refus décisif."""
    reasons: list[str] = []
    if not candidate.source:
        return QualificationVerdict(QualificationStatus.REJECTED, ["source inconnue"], 4,
                                        source=candidate.source)
    if not candidate.license or candidate.license not in LICENSE_ALLOWLIST:
        return QualificationVerdict(
            QualificationStatus.REJECTED,
            [f"licence incompatible ou absente: {candidate.license!r}"],
            4,
            source=candidate.source,
        )
    sensitive = sorted(set(candidate.permissions) & SENSITIVE_PERMISSIONS)
    if sensitive:
        return QualificationVerdict(
            QualificationStatus.QUARANTINED,
            [f"permissions sensibles: {sensitive} — revue humaine requise"],
            4,
            source=candidate.source,
        )
    if len(candidate.dependencies) > MAX_DEPENDENCIES:
        return QualificationVerdict(
            QualificationStatus.QUARANTINED,
            [f"{len(candidate.dependencies)} dépendances > {MAX_DEPENDENCIES}"],
            4,
            source=candidate.source,
        )
    if not candidate.has_tests:
        reasons.append("sans tests — adoption conditionnelle")
    if not candidate.sandbox_verified:
        return QualificationVerdict(
            QualificationStatus.CANDIDATE,
            reasons + ["bac à sable non vérifié — ne pas activer"],
            2,
            source=candidate.source,
        )
    return QualificationVerdict(
        QualificationStatus.QUALIFIED, reasons + ["grilles passées"], 2,
        source=candidate.source,
    )


def check_composition(chain: list[str], max_depth: int = MAX_CHAIN_DEPTH) -> dict[str, Any]:
    """Détecte cycles et dépassements dans une chaîne skill→skill→tool→model."""
    seen: set[str] = set()
    for i, name in enumerate(chain):
        if name in seen:
            return {"ok": False, "error": f"cycle détecté sur {name!r} à la position {i}"}
        seen.add(name)
    if len(chain) > max_depth:
        return {"ok": False, "error": f"profondeur {len(chain)} > {max_depth}"}
    return {"ok": True, "depth": len(chain)}
