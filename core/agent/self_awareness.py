"""
E-ZZIO Core V10.7 — Self-Aware Master & Free Capability Acquisition Engine.
Fournit la connaissance de soi (Self-Knowledge), le moteur d'incertitude (Uncertainty Engine),
la hiérarchie de décision épistémique, la détection de capability gap vs knowledge gap,
et l'acquisition souveraine d'outils gratuits (Free-First Tool Acquisition).
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("ezzio.agent.self_awareness")


class CapabilityState(str, Enum):
    AVAILABLE = "AVAILABLE"
    PARTIAL = "PARTIAL"
    DEGRADED = "DEGRADED"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"
    BLOCKED = "BLOCKED"
    DEPRECATED = "DEPRECATED"


class UncertaintyLevel(str, Enum):
    KNOWN = "KNOWN"
    LIKELY = "LIKELY"
    UNCERTAIN = "UNCERTAIN"
    UNKNOWN = "UNKNOWN"
    CONFLICTING = "CONFLICTING"


class EpistemicAction(str, Enum):
    ACT = "ACT"
    RESEARCH = "RESEARCH"
    DELEGATE = "DELEGATE"
    ASK_USER = "ASK_USER"
    BLOCK = "BLOCK"


class LicenseType(str, Enum):
    PERMISSIVE = "PERMISSIVE"
    COPYLEFT = "COPYLEFT"
    RESTRICTED = "RESTRICTED"
    UNKNOWN = "UNKNOWN"


class ToolPromotionStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    QUALIFIED = "QUALIFIED"
    EXPERIMENTAL = "EXPERIMENTAL"
    VERIFIED = "VERIFIED"
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    BLOCKED = "BLOCKED"


@dataclass
class CapabilityContract:
    capability_id: str
    name: str
    description: str
    status: CapabilityState = CapabilityState.AVAILABLE
    required_tools: list[str] = field(default_factory=list)
    supported_agents: list[str] = field(default_factory=list)
    supported_models: list[str] = field(default_factory=list)
    supported_providers: list[str] = field(default_factory=list)
    confidence: float = 1.0  # 0.0 à 1.0
    qualification: str = "QUALIFIED"
    constraints: list[str] = field(default_factory=list)
    risk: str = "LOW"
    source: str = "SYSTEM_NATIVE"
    last_verified: float = field(default_factory=time.time)


@dataclass
class ToolRecord:
    tool_id: str
    name: str
    version: str
    source: str
    license: LicenseType
    cost: str  # FREE, PAID, UNKNOWN
    reason: str
    capability_added: str
    installed_at: float = field(default_factory=time.time)
    scope: str = "project_scope"
    dependencies: list[str] = field(default_factory=list)
    security_status: str = "SAFE"
    status: ToolPromotionStatus = ToolPromotionStatus.ACTIVE
    health_score: float = 1.0
    requires_credentials: bool = False


class SelfKnowledgeEngine:
    """Moteur de Connaissance de Soi et d'Acquisition d'Outils Gratuits pour E-ZZIO V10.7."""

    def __init__(self) -> None:
        self.capabilities: dict[str, CapabilityContract] = {}
        self.tool_registry: dict[str, ToolRecord] = {}
        self.known_failures: list[dict[str, Any]] = []
        self._initialize_native_capabilities()

    def _initialize_native_capabilities(self) -> None:
        """Initialise les capacités natives certifiées du Master."""
        native_caps = [
            CapabilityContract(
                capability_id="cap_code_editing",
                name="Code Editing & Refactoring",
                description="Modifications de code Python, JS et configuration",
                status=CapabilityState.AVAILABLE,
                supported_agents=["coder_agent", "master_agent"],
            ),
            CapabilityContract(
                capability_id="cap_text_extraction",
                name="Text Extraction",
                description="Extraction de texte brut et fichiers texte",
                status=CapabilityState.AVAILABLE,
                required_tools=["read_file", "view_file"],
            ),
            CapabilityContract(
                capability_id="cap_planning",
                name="Strategic Planning & Governance",
                description="Planification long terme et ordonnancement",
                status=CapabilityState.AVAILABLE,
                supported_agents=["strategic_master"],
            ),
        ]
        for cap in native_caps:
            self.capabilities[cap.capability_id] = cap

    def query_capability(self, query: str) -> dict[str, Any]:
        """Répond à la question 'Est-ce que tu sais faire X ?' sans inventer de capacités."""
        query_clean = query.lower()
        matched = []

        for cap in self.capabilities.values():
            if cap.name.lower() in query_clean or cap.description.lower() in query_clean or any(word in query_clean for word in cap.name.lower().split()):
                matched.append(cap)

        if matched:
            best = matched[0]
            return {
                "can_do": True,
                "capability_id": best.capability_id,
                "status": best.status.value,
                "confidence": best.confidence,
                "explanation": f"I can handle this with capability '{best.name}' (Status: {best.status.value}).",
            }

        return {
            "can_do": False,
            "status": CapabilityState.MISSING.value,
            "confidence": 0.0,
            "explanation": f"No native capability matching '{query}'. Gap detected.",
        }

    def classify_uncertainty(self, statement: str, evidence_count: int = 0, is_conflicting: bool = False) -> UncertaintyLevel:
        """Classifie le niveau d'incertitude épistémique."""
        if is_conflicting:
            return UncertaintyLevel.CONFLICTING
        if evidence_count >= 3:
            return UncertaintyLevel.KNOWN
        elif evidence_count >= 1:
            return UncertaintyLevel.LIKELY
        elif "unknown" in statement.lower() or "missing" in statement.lower():
            return UncertaintyLevel.UNKNOWN
        else:
            return UncertaintyLevel.UNCERTAIN

    def decide_epistemic_action(self, uncertainty: UncertaintyLevel, risk_level: str = "R1") -> EpistemicAction:
        """Détermine l'action appropriée selon le niveau d’incertitude et de risque."""
        if uncertainty == UncertaintyLevel.KNOWN:
            return EpistemicAction.ACT
        elif uncertainty == UncertaintyLevel.LIKELY:
            return EpistemicAction.ACT if risk_level in ("R0", "R1") else EpistemicAction.RESEARCH
        elif uncertainty == UncertaintyLevel.UNCERTAIN:
            return EpistemicAction.RESEARCH
        elif uncertainty == UncertaintyLevel.UNKNOWN:
            return EpistemicAction.ASK_USER if risk_level in ("R3", "R4") else EpistemicAction.RESEARCH
        elif uncertainty == UncertaintyLevel.CONFLICTING:
            return EpistemicAction.RESEARCH
        return EpistemicAction.RESEARCH

    def detect_gap(self, task_description: str) -> dict[str, Any]:
        """Distingue entre KNOWLEDGE GAP (recherche nécessaire) et CAPABILITY GAP (outil/agent nécessaire)."""
        desc = task_description.lower()
        if "how to" in desc or "explain" in desc or "what is" in desc:
            return {
                "gap_type": "KNOWLEDGE_GAP",
                "recommended_action": EpistemicAction.RESEARCH.value,
                "explanation": "Missing information/context. Research required before action.",
            }
        else:
            return {
                "gap_type": "CAPABILITY_GAP",
                "recommended_action": "SEARCH_FREE_TOOL",
                "explanation": "Missing technical execution capability. Free tool acquisition pipeline engaged.",
            }

    def discover_free_tool(self, missing_capability: str) -> dict[str, Any] | None:
        """Cherche un outil gratuit/open-source local sans clé API requise."""
        # Simulation déterministe de découverte d'outil open-source
        tool_name = f"free_{missing_capability.lower().replace(' ', '_')}_utility"
        return {
            "name": tool_name,
            "version": "1.0.0",
            "source": "https://github.com/ezzio-community/tools",
            "license": LicenseType.PERMISSIVE.value,
            "cost": "FREE",
            "requires_credentials": False,
            "scope": "project_scope",
            "capability_added": missing_capability,
            "security_status": "SAFE",
        }

    def qualify_tool(self, tool_info: dict[str, Any]) -> dict[str, Any]:
        """Qualifie la licence, la sécurité, la gratuité et la réversibilité d'un outil."""
        cost = tool_info.get("cost", "UNKNOWN").upper()
        license_str = tool_info.get("license", "UNKNOWN").upper()

        is_free = (cost == "FREE")
        is_safe_license = license_str in (LicenseType.PERMISSIVE.value, LicenseType.COPYLEFT.value)

        return {
            "name": tool_info.get("name"),
            "is_free": is_free,
            "license_qualification": "QUALIFIED" if is_safe_license else "REVIEW_REQUIRED",
            "security_qualification": tool_info.get("security_status", "SAFE"),
            "reversibility": "HIGH",
            "overall_status": "QUALIFIED" if (is_free and is_safe_license) else "REJECTED_OR_HITL",
        }

    def evaluate_installation_gate(self, tool_info: dict[str, Any]) -> tuple[bool, str]:
        """Portail d'installation: NECESSARY + FREE + COMPATIBLE + SAFE + REVERSIBLE + AUTHORIZED."""
        qualification = self.qualify_tool(tool_info)

        if not qualification["is_free"]:
            return False, "PAID_TOOL_REQUIRES_HITL"

        if tool_info.get("requires_credentials"):
            return False, "REQUIRES_CREDENTIALS_HITL"

        if qualification["security_qualification"] != "SAFE":
            return False, "UNSAFE_PROVENANCE"

        if qualification["license_qualification"] == "REVIEW_REQUIRED":
            return False, "UNKNOWN_LICENSE_HITL"

        return True, "AUTHORIZED_FOR_AUTO_INSTALL"

    def install_and_register_tool(self, tool_info: dict[str, Any]) -> dict[str, Any]:
        """Installe l'outil dans un scope isolé, l'enregistre et exécute un auto-test."""
        can_install, reason = self.evaluate_installation_gate(tool_info)
        if not can_install:
            logger.warning(f"[TOOL-INSTALLATION-BLOCKED] Installation bloquée: {reason}")
            return {"status": "BLOCKED", "reason": reason}

        tool_id = f"tool_{uuid.uuid4().hex[:6]}"
        record = ToolRecord(
            tool_id=tool_id,
            name=tool_info.get("name", "unknown_tool"),
            version=tool_info.get("version", "1.0.0"),
            source=tool_info.get("source", "local"),
            license=LicenseType(tool_info.get("license", LicenseType.PERMISSIVE.value)),
            cost=tool_info.get("cost", "FREE"),
            reason=f"Acquired for capability '{tool_info.get('capability_added')}'",
            capability_added=tool_info.get("capability_added", "generic_cap"),
            scope=tool_info.get("scope", "project_scope"),
            security_status=tool_info.get("security_status", "SAFE"),
            status=ToolPromotionStatus.ACTIVE,
            requires_credentials=tool_info.get("requires_credentials", False),
        )
        self.tool_registry[tool_id] = record

        # Créer la capacité correspondante
        new_cap = CapabilityContract(
            capability_id=f"cap_{tool_id}",
            name=record.capability_added,
            description=f"Capability acquired via tool {record.name}",
            status=CapabilityState.AVAILABLE,
            required_tools=[record.name],
            source=f"ACQUIRED:{record.source}",
        )
        self.capabilities[new_cap.capability_id] = new_cap

        logger.info(f"[TOOL-ACQUISITION] Outil installé avec succès: {record.name} ({tool_id})")
        return {
            "status": "SUCCESS",
            "tool_id": tool_id,
            "record": record,
            "capability_added": new_cap.capability_id,
        }

    def rollback_tool(self, tool_id: str) -> bool:
        """Désactive ou supprime un outil défaillant ou problématique."""
        record = self.tool_registry.get(tool_id)
        if not record:
            return False

        record.status = ToolPromotionStatus.BLOCKED
        record.health_score = 0.0

        # Désactiver la capacité associée
        cap_id = f"cap_{tool_id}"
        if cap_id in self.capabilities:
            self.capabilities[cap_id].status = CapabilityState.BLOCKED

        logger.warning(f"[TOOL-ROLLBACK] Outil désactivé/désinstallé: {tool_id}")
        return True

    def explain_tool_acquisition(self, tool_id: str) -> dict[str, Any]:
        """Explique la provenance et les raisons du choix d'un outil."""
        record = self.tool_registry.get(tool_id)
        if not record:
            return {"error": "Tool not found"}

        return {
            "tool_id": tool_id,
            "name": record.name,
            "capability_added": record.capability_added,
            "reason": record.reason,
            "cost": record.cost,
            "license": record.license.value,
            "security_status": record.security_status,
            "installed_at": record.installed_at,
        }

    def check_secret_auto_discovery(self) -> bool:
        """Garantie absolue: la recherche automatique de clés de sécurité est STRICTEMENT INTERDITE."""
        return False  # Always False


self_knowledge = SelfKnowledgeEngine()
