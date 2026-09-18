"""
E-ZZIO Core — Capability Qualification Contract & Schema.
Fournit le schéma de validation strict pour l'enregistrement de toute capacité externe ou plugin.
"""
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class QualificationStatus(str, Enum):
    QUALIFIED = "QUALIFIED"
    CANDIDATE = "CANDIDATE"
    QUARANTINED = "QUARANTINED"
    REJECTED = "REJECTED"


class CapabilityQualification(BaseModel):
    name: str = Field(..., description="Nom unique de la capacité (ex: web-search-mcp, crawl4ai)")
    category: str = Field(..., description="Catégorie : perception, web, saas, model, browser")
    provider: str = Field(..., description="Fournisseur ou brique sous-jacente")
    input_contract: dict[str, Any] = Field(..., description="Schéma des entrées attendues")
    output_contract: dict[str, Any] = Field(..., description="Schéma des sorties produites (donnée passive)")
    permissions: list[str] = Field(default_factory=list, description="Liste des permissions requises")
    network_access: bool = Field(False, description="Nécessite un accès réseau externe")
    secrets_required: list[str] = Field(default_factory=list, description="Clés secrètes requises (depuis key_vault)")
    filesystem_access: str = Field("NONE", description="NONE, READ_ONLY_SANDBOX, WRITE_SANDBOX")
    subprocess_access: bool = Field(False, description="Autorisation d'exécuter des sous-processus")
    ssrf_protection: bool = Field(True, description="Protection anti-SSRF et IP Pinning activée")
    timeout_seconds: float = Field(30.0, description="Délai maximum d'exécution")
    max_payload_mb: float = Field(50.0, description="Taille maximale du payload en Mo")
    audit_events: bool = Field(True, description="Journalisation forensique obligatoire")
    fail_closed: bool = Field(True, description="Comportement Fail-Closed en cas d'erreur")
    fallback_behavior: str = Field("GRACEFUL_DEGRADE", description="Comportement de repli")
    tests_reference: list[str] = Field(default_factory=list, description="Chemins des tests unitaires validant la capacité")
    status: QualificationStatus = Field(QualificationStatus.QUALIFIED, description="Statut de qualification")
    source: str | None = Field(None, description="Provenance (interne, github:owner/repo, url)")
    version: str | None = Field(None, description="Version de la capacité")
    license: str | None = Field(None, description="Licence SPDX (ex: MIT, Apache-2.0)")
