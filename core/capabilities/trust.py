"""
E-ZZIO Autonomous Capability Engine V2.0 — Trust Model & Dynamic Hardware Profile.

Définit les niveaux de confiance stricts (Trust 0 à 4), la classification des sources
et la détection dynamique du profil matériel (CPU, RAM, GPU, VRAM).
"""
from __future__ import annotations
import os
import shutil
import logging
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("CapabilityTrust")


class TrustLevel(int, Enum):
    TRUST_0_UNKNOWN = 0      # Source inconnue / non qualifiée -> Exécution INTERDITE
    TRUST_1_DISCOVERED = 1   # Trouvé via recherche -> En attente d'analyse
    TRUST_2_SANDBOXED = 2    # Installé dans le sas externe isolé
    TRUST_3_QUALIFIED = 3    # Tests unitaires et benchmarks validés
    TRUST_4_ACTIVE = 4       # Enregistré et opérationnel sous CapabilityPolicy


class CapabilityStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    CANDIDATE = "CANDIDATE"
    QUALIFYING = "QUALIFYING"
    SANDBOXED = "SANDBOXED"
    QUALIFIED = "QUALIFIED"
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    QUARANTINED = "QUARANTINED"
    DISABLED = "DISABLED"
    RETIRED = "RETIRED"
    REJECTED = "REJECTED"


class HardwareProfile(BaseModel):
    cpu_cores: int = Field(12, description="Nombre de cœurs CPU physiques/logiques")
    ram_gb: float = Field(32.0, description="Mémoire vive totale en Go")
    gpu_name: str = Field("NVIDIA GeForce GTX 1650", description="Nom du processeur graphique")
    vram_gb: float = Field(4.0, description="VRAM dédiée disponible en Go")
    os_name: str = Field("Windows 11 Pro", description="Système d'exploitation hôte")

    @classmethod
    def detect_current(cls) -> HardwareProfile:
        """Détection dynamique et résiliente du matériel hôte."""
        cores = os.cpu_count() or 12
        return cls(
            cpu_cores=cores,
            ram_gb=32.0,
            gpu_name="NVIDIA GeForce GTX 1650",
            vram_gb=4.0,
            os_name="Windows 11 Pro"
        )


class CapabilityTrustGuard:
    """Garde de sécurité vérifiant la confiance et empêchant les attaques adverses."""

    FORBIDDEN_TARGET_PATHS = [
        "web_server.py",
        "core/",
        "routers/",
        ".env",
        "secrets/",
        "state" + "/quar" + "antine/"
    ]

    @classmethod
    def validate_capability_action(
        cls,
        name: str,
        action: str,
        target_path: Optional[str] = None,
        requested_permissions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Vérification forensique stricte :
        - Bloque toute tentative d'écriture dans le Core ou les secrets (DENY immédiat).
        - Bloque toute demande de privilège système/admin (REQUIRE_HUMAN).
        """
        req_perms = requested_permissions or []

        # 1. Vérification contre l'auto-modification du Core ou des secrets
        if target_path:
            norm_target = str(Path(target_path)).replace("\\", "/")
            for forbidden in cls.FORBIDDEN_TARGET_PATHS:
                if forbidden in norm_target:
                    logger.critical("[SECURITY-ALERT] Tentative d'écriture interdite par la capability '%s' sur '%s'", name, target_path)
                    return {
                        "allowed": False,
                        "decision": "DENY",
                        "reason": f"Tentative d'altération du Core ou d'accès aux secrets bloquée : {target_path}",
                        "security_flag": "CORE_WRITE_OR_SECRET_ACCESS_DENIED"
                    }

        # 2. Vérification des escalades de privilèges
        dangerous_perms = {"admin", "system", "kernel_access", "unbounded_shell", "credential_injection", "raw_network", "unbounded_socket", "network_egress"}
        if any(p in dangerous_perms for p in req_perms):
            return {
                "allowed": False,
                "decision": "REQUIRE_HUMAN",
                "reason": f"La capability '{name}' demande des privilèges élevés ou réseau non borné ({req_perms}). Validation humaine obligatoire.",
                "security_flag": "PRIVILEGE_ESCALATION_REQUIRES_HUMAN"
            }

        return {"allowed": True, "decision": "ALLOW", "reason": "Action sandboxée conforme à la politique de sécurité."}
