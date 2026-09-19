"""
E-ZZIO Autonomous Capability Engine V2.0 — Discovery & Evaluation Pipeline.

Recherche, évalue et score de manière autonome les capacités selon les règles de confiance,
de licence et de profil matériel dynamique.
"""
from __future__ import annotations

import logging
import unicodedata
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from core.capabilities.trust import CapabilityStatus, HardwareProfile, TrustLevel

logger = logging.getLogger("CapabilityDiscovery")


class SourceTrustLevel(StrEnum):
    OFFICIAL_PROJECT = "OFFICIAL_PROJECT"
    VERIFIED_ORGANIZATION = "VERIFIED_ORGANIZATION"
    ESTABLISHED_OPEN_SOURCE = "ESTABLISHED_OPEN_SOURCE"
    COMMUNITY_PROJECT = "COMMUNITY_PROJECT"
    UNKNOWN = "UNKNOWN"


class LicenseClass(StrEnum):
    PERMISSIVE = "PERMISSIVE"          # MIT, Apache-2.0, BSD, Unlicense
    COPYLEFT_SAFE = "COPYLEFT_SAFE"    # GPL, LGPL (Externe/Sandbox)
    NON_COMMERCIAL = "NON_COMMERCIAL"  # CC-BY-NC (Rejet souverain)
    RESTRICTED = "RESTRICTED"          # Propriétaire / Restreint
    UNKNOWN = "UNKNOWN"


class CapabilityProposal(BaseModel):
    name: str = Field(..., description="Nom de la capacité candidate")
    category: str = Field(..., description="image, audio, video, document, web, saas, code, animation")
    description: str = Field(..., description="Rôle et cas d'usage")
    source_repository: str = Field(..., description="URL ou identifiant du dépôt officiel")
    trust_level: TrustLevel = Field(TrustLevel.TRUST_1_DISCOVERED)
    source_trust: SourceTrustLevel = Field(SourceTrustLevel.COMMUNITY_PROJECT)
    code_license: str = Field("UNKNOWN")
    weights_license: str | None = Field("N/A")
    license_class: LicenseClass = Field(LicenseClass.UNKNOWN)
    commercial_allowed: bool = Field(False)
    locality: str = Field("LOCAL_SANDBOX", description="LOCAL_REAL, LOCAL_CPU, LOCAL_SANDBOX, CLOUD_API")
    min_vram_gb: float = Field(0.0)
    min_ram_gb: float = Field(1.0)
    hardware_fit: bool = Field(True)
    required_permissions: list[str] = Field(default_factory=list)
    risk_level: str = Field("LOW", description="LOW, MEDIUM, HIGH, CRITICAL")
    install_target: str = Field("G:\\AI\\external\\capabilities\\")
    score: float = Field(0.0, description="Score composite 0-10")
    status: CapabilityStatus = Field(CapabilityStatus.DISCOVERED)


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


class CapabilityDiscoveryEngine:
    """Moteur souverain de découverte, d'analyse et de scoring de capacités."""

    def __init__(self, workspace_root: str = "G:\\AI\\E-zzio"):
        self.workspace_root = Path(workspace_root).resolve()
        self.hardware = HardwareProfile.detect_current()
        self.known_catalog = self._init_known_catalog()

    def _init_known_catalog(self) -> dict[str, dict[str, Any]]:
        return {
            "kokoro-tts": {
                "category": "audio",
                "desc": "Synthèse vocale ultra-rapide Apache 2.0 sur CPU (<90ms)",
                "repo": "https://github.com/hexgrad/Kokoro-82M",
                "code_lic": "Apache-2.0",
                "weights_lic": "Apache-2.0",
                "comm": True,
                "vram": 0.0,
                "ram": 0.5,
                "risk": "LOW",
                "functional_value": 9.5,
                "locality": "LOCAL_CPU"
            },
            "ltx-video": {
                "category": "video",
                "desc": "Génération vidéo DiT temps réel en FP8/GGUF sur 4GB VRAM",
                "repo": "https://github.com/Lightricks/LTX-Video",
                "code_lic": "Apache-2.0",
                "weights_lic": "Apache-2.0",
                "comm": True,
                "vram": 3.8,
                "ram": 6.0,
                "risk": "MEDIUM",
                "functional_value": 9.4,
                "locality": "LOCAL_REAL"
            },
            "liveportrait": {
                "category": "animation",
                "desc": "Animation de portrait et transfert de mouvement facial en 2.5GB VRAM",
                "repo": "https://github.com/KwaiVGI/LivePortrait",
                "code_lic": "MIT",
                "weights_lic": "Research Non-Commercial",
                "comm": False,
                "vram": 2.5,
                "ram": 3.0,
                "risk": "MEDIUM",
                "functional_value": 8.8,
                "locality": "LOCAL_REAL"
            },
            "f5-tts": {
                "category": "audio",
                "desc": "Clonage vocal Diffusion Transformer (Poids Non-Commerciaux)",
                "repo": "https://github.com/SWivid/F5-TTS",
                "code_lic": "MIT",
                "weights_lic": "CC-BY-NC-4.0",
                "comm": False,
                "vram": 2.0,
                "ram": 3.0,
                "risk": "HIGH",
                "functional_value": 7.0,
                "locality": "LOCAL_REAL"
            },
            "wan2.1-moe": {
                "category": "video",
                "desc": "Génération vidéo haute fidélité (Exige 16-24GB VRAM)",
                "repo": "https://github.com/Wan-Video/Wan2.1",
                "code_lic": "Apache-2.0",
                "weights_lic": "Open Weights",
                "comm": True,
                "vram": 16.0,
                "ram": 24.0,
                "risk": "HIGH",
                "functional_value": 8.5,
                "locality": "CLOUD_REMOTE"
            },
            "nvidia-nim": {
                "category": "multimodal",
                "desc": "Inférence LLM et diffusion d'images via microservices NVIDIA NIM (Build.NVIDIA)",
                "repo": "https://build.nvidia.com",
                "code_lic": "Apache-2.0",
                "weights_lic": "Cloud Hosted",
                "comm": True,
                "vram": 0.0,
                "ram": 0.2,
                "risk": "LOW",
                "functional_value": 9.0,
                "locality": "CLOUD_API"
            }
        }

    def compute_score(self, data: dict[str, Any], fit: bool) -> float:
        """Calcule un score déterministe basé sur l'utilité, la sécurité, la localité et la licence."""
        val = data.get("functional_value", 7.0)
        lic_penalty = 0.0 if data.get("comm") else 2.0
        hw_penalty = 0.0 if fit else 4.0
        risk_penalty = 0.0 if data.get("risk") == "LOW" else (0.5 if data.get("risk") == "MEDIUM" else 1.5)
        score = max(0.0, min(10.0, val - lic_penalty - hw_penalty - risk_penalty))
        return round(score, 1)

    def discover_capability_for_task(self, query: str) -> list[CapabilityProposal]:
        """Recherche et qualifie les propositions candidates pour un besoin donné."""
        q_clean = strip_accents(query.lower())
        proposals = []

        for key, data in self.known_catalog.items():
            cat = data["category"]
            if (
                key in q_clean or
                cat in q_clean or
                (cat == "video" and "video" in q_clean) or
                (cat == "audio" and any(k in q_clean for k in ("audio", "voix", "tts", "parole"))) or
                (cat == "animation" and any(k in q_clean for k in ("animation", "portrait", "visage")))
            ):
                comm = data["comm"]
                vram = data["vram"]
                fit = vram <= self.hardware.vram_gb

                lic_class = LicenseClass.PERMISSIVE if comm else LicenseClass.NON_COMMERCIAL
                score = self.compute_score(data, fit)
                status = CapabilityStatus.QUALIFIED if (fit and comm) else (CapabilityStatus.SANDBOXED if fit else CapabilityStatus.REJECTED)
                trust = TrustLevel.TRUST_3_QUALIFIED if status == CapabilityStatus.QUALIFIED else TrustLevel.TRUST_2_SANDBOXED

                prop = CapabilityProposal(
                    name=key,
                    category=data["category"],
                    description=data["desc"],
                    source_repository=data["repo"],
                    trust_level=trust,
                    source_trust=SourceTrustLevel.VERIFIED_ORGANIZATION,
                    code_license=data["code_lic"],
                    weights_license=data["weights_lic"],
                    license_class=lic_class,
                    commercial_allowed=comm,
                    locality=data.get("locality", "LOCAL_SANDBOX"),
                    min_vram_gb=vram,
                    min_ram_gb=data["ram"],
                    hardware_fit=fit,
                    required_permissions=["local_execute"],
                    risk_level=data["risk"],
                    install_target=f"G:\\AI\\external\\capabilities\\{key}\\",
                    score=score,
                    status=status
                )
                proposals.append(prop)

        # Trier par score décroissant
        proposals.sort(key=lambda p: p.score, reverse=True)
        return proposals
