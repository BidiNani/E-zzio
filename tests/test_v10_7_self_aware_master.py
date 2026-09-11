"""
E-ZZIO Core V10.7 — Test Suite for Self-Aware Master & Free Capability Acquisition.
Valide les requêtes de connaissances de soi, la classification de l'incertitude,
la détection de capability gap vs knowledge gap, le portail Free-First d'installation d'outils,
et les invariants de sécurité (No Secret Auto-Discovery, HITL sur outils payants).
"""
import pytest
from core.agent.self_awareness import (
    SelfKnowledgeEngine,
    CapabilityState,
    UncertaintyLevel,
    EpistemicAction,
    LicenseType,
    ToolPromotionStatus,
)


@pytest.fixture
def self_engine():
    return SelfKnowledgeEngine()


def test_01_capability_query_native(self_engine):
    """Scenario A: Capacité native existante identifiée sans besoin d'installation."""
    res = self_engine.query_capability("Code Editing")
    assert res["can_do"] is True
    assert res["capability_id"] == "cap_code_editing"
    assert res["status"] == CapabilityState.AVAILABLE.value


def test_02_capability_query_missing(self_engine):
    """Vérifie la détection d'une capacité absente."""
    res = self_engine.query_capability("Quantum Encryption Analysis")
    assert res["can_do"] is False
    assert res["status"] == CapabilityState.MISSING.value


def test_03_gap_detection_knowledge_vs_capability(self_engine):
    """Scenario D & E: Distingue Knowledge Gap (recherche) et Capability Gap (acquisition d'outil)."""
    k_gap = self_engine.detect_gap("How to configure Ollama GPU layers?")
    assert k_gap["gap_type"] == "KNOWLEDGE_GAP"
    assert k_gap["recommended_action"] == EpistemicAction.RESEARCH.value

    c_gap = self_engine.detect_gap("Convert PDF rendering to SVG vectors")
    assert c_gap["gap_type"] == "CAPABILITY_GAP"
    assert c_gap["recommended_action"] == "SEARCH_FREE_TOOL"


def test_04_uncertainty_classification_and_epistemic_actions(self_engine):
    """Vérifie la classification de l'incertitude et la décision d'action épistémique."""
    u_known = self_engine.classify_uncertainty("Verified state", evidence_count=3)
    assert u_known == UncertaintyLevel.KNOWN
    assert self_engine.decide_epistemic_action(u_known) == EpistemicAction.ACT

    u_unknown = self_engine.classify_uncertainty("Unknown status", evidence_count=0)
    assert u_unknown == UncertaintyLevel.UNKNOWN
    assert self_engine.decide_epistemic_action(u_unknown, risk_level="R3") == EpistemicAction.ASK_USER


def test_05_free_tool_discovery_and_qualification(self_engine):
    """Vérifie la découverte et la qualification d'un outil gratuit open-source."""
    tool = self_engine.discover_free_tool("PDF Rendering")
    assert tool["cost"] == "FREE"
    assert tool["license"] == LicenseType.PERMISSIVE.value

    qual = self_engine.qualify_tool(tool)
    assert qual["is_free"] is True
    assert qual["overall_status"] == "QUALIFIED"


def test_06_installation_gate_authorized(self_engine):
    """Scenario E: Outil gratuit et sûr autorisé pour l'auto-installation."""
    tool = self_engine.discover_free_tool("Image Resizing")
    can_install, reason = self_engine.evaluate_installation_gate(tool)

    assert can_install is True
    assert reason == "AUTHORIZED_FOR_AUTO_INSTALL"

    res = self_engine.install_and_register_tool(tool)
    assert res["status"] == "SUCCESS"
    assert "tool_id" in res


def test_07_installation_gate_paid_tool_blocked(self_engine):
    """Scenario F: Outil payant bloqué par la gate et nécessitant un accord utilisateur (HITL)."""
    paid_tool = {
        "name": "commercial_pdf_sdk",
        "cost": "PAID",
        "license": LicenseType.RESTRICTED.value,
        "security_status": "SAFE",
    }
    can_install, reason = self_engine.evaluate_installation_gate(paid_tool)

    assert can_install is False
    assert reason == "PAID_TOOL_REQUIRES_HITL"

    res = self_engine.install_and_register_tool(paid_tool)
    assert res["status"] == "BLOCKED"


def test_08_tool_rollback_and_capability_disable(self_engine):
    """Scenario J: Rollback/Désactivation d'un outil défaillant."""
    tool = self_engine.discover_free_tool("Audio Synthesizer")
    res = self_engine.install_and_register_tool(tool)
    tool_id = res["tool_id"]

    # Rollback
    rolled_back = self_engine.rollback_tool(tool_id)
    assert rolled_back is True

    record = self_engine.tool_registry[tool_id]
    assert record.status == ToolPromotionStatus.BLOCKED
    assert record.health_score == 0.0


def test_09_decision_explanation(self_engine):
    """Vérifie la réponse déterministe et l'explication d'acquisition d'outil."""
    tool = self_engine.discover_free_tool("Graph Visualizer")
    res = self_engine.install_and_register_tool(tool)
    tool_id = res["tool_id"]

    explanation = self_engine.explain_tool_acquisition(tool_id)
    assert explanation["tool_id"] == tool_id
    assert explanation["cost"] == "FREE"
    assert explanation["license"] == LicenseType.PERMISSIVE.value


def test_10_no_secret_auto_discovery_invariant(self_engine):
    """Invariant de Sécurité Absolute: La recherche automatique de secrets est strictement interdite."""
    assert self_engine.check_secret_auto_discovery() is False
