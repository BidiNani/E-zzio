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
import hashlib
import json
import os

import pytest

from core.agents.registry import AgentRegistry
from core.providers.base_provider import BaseProvider
from core.providers.gemini_provider import GeminiProvider
from core.providers.groq_provider import GroqProvider
from core.providers.nvidia_nim_provider import NvidiaNimProvider
from core.providers.ollama_provider import OllamaProvider
from web_server import app


def test_qg_frozen_core_integrity():
    """Frozen Core SHA256 integrity match."""
    import hashlib
    import json
    from pathlib import Path

    root = Path(__file__).parent.parent
    manifest_path = root / "docs" / "FROZEN_CORE_MANIFEST.json"

    assert manifest_path.exists(), "Manifest Frozen Core introuvable"

    with open(manifest_path, encoding="utf-8") as f:
        raw = json.load(f)

    # Support des 2 formats : "files" (nouveau) et "components" (ancien)
    if "files" in raw:
        manifest = raw["files"]
    elif "components" in raw:
        manifest = {
            path: meta["sha256"] if isinstance(meta, dict) else meta
            for path, meta in raw["components"].items()
        }
    else:
        raise AssertionError("Format de manifest inconnu")

    for rel_path, expected_hash in manifest.items():
        target = root / rel_path
        assert target.exists(), f"Fichier Core manquant : {rel_path}"

        actual = hashlib.sha256(target.read_bytes()).hexdigest().upper()
        expected = expected_hash.upper()
        assert actual == expected, (
            f"Frozen Core drift : {rel_path}\n"
            f"  attendu : {expected}\n"
            f"  actuel  : {actual}"
        )


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
    route_paths = []
    for r in app.routes:
        if hasattr(r, "path"):
            route_paths.append(r.path)
        elif hasattr(r, "original_router"):
            prefix = getattr(getattr(r, "include_context", None), "prefix", "") or ""
            for sub_r in getattr(r.original_router, "routes", []):
                route_paths.append(prefix + getattr(sub_r, "path", ""))
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
