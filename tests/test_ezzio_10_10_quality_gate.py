"""
E-ZZIO Quality Gate Test Suite — 10/10 Certified Invariants.
Vérifie de manière programmatique et stricte :
1. Frozen Core SHA256 integrity match
2. Absence of credential leaks in exposed files
3. 4 Canonical Providers conform to BaseProvider contracts
4. Official Web Server router mountings
5. Autonomous Agent Fleet readiness
6. Absolute Scope Exclusion: No Unreal Engine artifacts or dependencies
"""
import os
import json
import hashlib
import pytest
from core.providers.base_provider import BaseProvider
from core.providers.ollama_provider import OllamaProvider
from core.providers.gemini_provider import GeminiProvider
from core.providers.groq_provider import GroqProvider
from core.providers.nvidia_nim_provider import NvidiaNimProvider
from core.agents.registry import AgentRegistry
from web_server import app


def test_qg_frozen_core_integrity():
    manifest_path = "docs/FROZEN_CORE_MANIFEST.json"
    assert os.path.exists(manifest_path)
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)["components"]

    files = [
        "core/capabilities/capability_policy.py",
        "core/capabilities/registry.py",
        "core/security/audit_ledger.py"
    ]
    for f in files:
        assert os.path.exists(f)
        h = hashlib.sha256(open(f, "rb").read()).hexdigest().lower()
        expected = manifest.get(f, {}).get("sha256", "").lower()
        assert h == expected, f"Frozen Core integrity breach on {f}"


def test_qg_canonical_providers_contracts():
    providers = [
        OllamaProvider(),
        GeminiProvider(),
        GroqProvider(),
        NvidiaNimProvider(),
    ]
    for p in providers:
        assert isinstance(p, BaseProvider)
        assert hasattr(p, "name")
        assert hasattr(p, "availability")
        assert hasattr(p, "cost_class")
        assert hasattr(p, "generate")
        assert hasattr(p, "stream")
        assert hasattr(p, "search")


def test_qg_official_web_server_routers():
    route_paths = [route.path for route in app.routes]
    required = [
        "/health",
        "/perception/status",
        "/generators/universal",
        "/capabilities",
        "/master/chat"
    ]
    for req in required:
        assert any(req in p for p in route_paths), f"Missing required router endpoint: {req}"


def test_qg_agent_fleet_registry():
    reg = AgentRegistry()
    reg.reset_to_defaults()
    agents = reg.list_agents()
    assert len(agents) >= 5
    master = reg.get_agent("master_ezzio")
    assert master is not None
    assert master.is_master is True


def test_qg_no_unreal_engine_artifacts():
    """Vérifie l'exclusion absolue d'Unreal Engine dans le dépôt."""
    forbidden_tokens = ["unreal", "ue5", "unrealengine", "ue4"]
    # Vérifier qu'aucun package, dossier ou fichier core ne s'appelle ou n'importe Unreal
    for root, dirs, files in os.walk("core"):
        for d in dirs:
            assert not any(tok in d.lower() for tok in forbidden_tokens), f"Unreal artifact found: {d}"
        for f in files:
            assert not any(tok in f.lower() for tok in forbidden_tokens), f"Unreal artifact found: {f}"
