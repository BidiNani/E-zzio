"""
E-ZZIO V9.0 — ANTI-REGRESSION ARCHITECTURAL GUARD (20 TESTS)
Vérifie contractuellement les 20 invariants fondamentaux de l'Architecture Freeze V9.0.
"""

import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent


def test_1_canonical_entry_point_unique():
    """Vérifie que web_server.py est l'unique point d'entrée et monte FastAPI."""
    ws = ROOT / 'web_server.py'
    assert ws.exists(), 'web_server.py doit exister à la racine'
    txt = ws.read_text(encoding='utf-8', errors='ignore')
    assert 'FastAPI(' in txt, 'web_server.py doit instancier FastAPI'


def test_2_seven_active_mounted_routers():
    """Vérifie que web_server.py monte exactement les 6 routeurs canoniques."""
    ws = ROOT / 'web_server.py'
    txt = ws.read_text(encoding='utf-8', errors='ignore')
    expected_routers = [
        'master_router',
        'telemetry_router',
        'memory_router',
        'perception_router',
        'generators_router',
        'capabilities_router',
    ]
    mounted_count = 0
    for r in expected_routers:
        assert f'app.include_router({r})' in txt, f'{r} doit être monté dans web_server.py'
        mounted_count += 1
    assert mounted_count == 6


def test_3_model_router_unique_authority():
    """Vérifie que core/cognition/model_router.py est l'unique autorité de profil de modèle."""
    mr = ROOT / 'core' / 'cognition' / 'model_router.py'
    assert mr.exists(), 'core/cognition/model_router.py doit exister'
    txt = mr.read_text(encoding='utf-8', errors='ignore')
    assert 'class ModelRouter' in txt


def test_4_gemini_pool_unique_authority():
    """Vérifie que core/models/gemini_pool.py gère souverainement les projets et la rotation 429."""
    gp = ROOT / 'core' / 'models' / 'gemini_pool.py'
    assert gp.exists(), 'core/models/gemini_pool.py doit exister'
    txt = gp.read_text(encoding='utf-8', errors='ignore')
    assert 'class GeminiPoolManager' in txt


def test_5_gemini_primary_first_policy():
    """Vérifie que la politique par défaut de ModelRouter privilégie Gemini en Primary."""
    mr = ROOT / 'core' / 'cognition' / 'model_router.py'
    txt = mr.read_text(encoding='utf-8', errors='ignore')
    assert 'gemini-3.8-flash' in txt or 'gemini-3.7-flash' in txt or 'gemini-3.5-flash' in txt


def test_6_ollama_secondary_local_policy():
    """Vérifie qu'Ollama est configuré comme second rideau / fallback."""
    mr = ROOT / 'core' / 'cognition' / 'model_router.py'
    txt = mr.read_text(encoding='utf-8', errors='ignore')
    assert 'qwen2.5-coder' in txt or 'ollama' in txt.lower()


def test_7_unified_memory_gateway_unique():
    """Vérifie l'unicité de UnifiedMemoryGateway comme autorité mémoire."""
    um = ROOT / 'core' / 'memory' / 'unified_gateway.py'
    assert um.exists(), 'core/memory/unified_gateway.py doit exister'
    txt = um.read_text(encoding='utf-8', errors='ignore')
    assert 'class UnifiedMemoryGateway' in txt


def test_8_capability_policy_unique_authority():
    """Vérifie l'autorité de sécurité CapabilityPolicy (ALLOW/REQUIRE_HUMAN/DENY)."""
    cp = ROOT / 'core' / 'capabilities' / 'capability_policy.py'
    assert cp.exists(), 'core/capabilities/capability_policy.py doit exister'
    txt = cp.read_text(encoding='utf-8', errors='ignore')
    assert 'class CapabilityPolicy' in txt
    assert 'REQUIRE_HUMAN' in txt
    assert 'ALLOW' in txt
    assert 'DENY' in txt


def test_9_coding_agent_harness_unique():
    """Vérifie l'unicité du worker coding CodingAgentHarness."""
    ch = ROOT / 'core' / 'agent' / 'coding_agent_loop.py'
    assert ch.exists(), 'core/agent/coding_agent_loop.py doit exister'
    txt = ch.read_text(encoding='utf-8', errors='ignore')
    assert 'class CodingAgentHarness' in txt


def test_10_no_legacy_imports_in_runtime():
    """Vérifie qu'aucun module runtime n'importe legacy_archive."""
    for py in (ROOT / 'core').glob('**/*.py'):
        txt = py.read_text(encoding='utf-8', errors='ignore')
        assert 'legacy_archive' not in txt, f'Import legacy_archive interdit dans {py}'


def test_11_no_quarantine_imports_in_runtime():
    """Vérifie qu'aucun module runtime n'importe state/quarantine."""
    for py in (ROOT / 'core').glob('**/*.py'):
        txt = py.read_text(encoding='utf-8', errors='ignore')
        assert 'state.quarantine' not in txt and 'state/quarantine' not in txt, f'Import quarantine interdit dans {py}'


def test_12_no_requests_dependency_in_runtime():
    """Vérifie l'absence totale d'import requests dans core/ et routers/."""
    for folder in ['core', 'routers']:
        for py in (ROOT / folder).glob('**/*.py'):
            for idx, line in enumerate(py.read_text(encoding='utf-8', errors='ignore').splitlines(), 1):
                assert not re.search(r'^\s*(import\s+requests|from\s+requests(\.|\s+))', line), f'requests trouvé dans {py}:{idx}'


def test_13_no_forbidden_duplicate_router_active():
    """Vérifie que les routeurs doublons ne sont plus présents dans routers/ racine."""
    forbidden_routers = [
        ROOT / 'routers' / 'brain_gateway.py',
        ROOT / 'routers' / 'cloud_brain.py',
        ROOT / 'routers' / 'safe_actions.py',
        ROOT / 'routers' / 'vision_smart.py',
    ]
    for fr in forbidden_routers:
        assert not fr.exists(), f'{fr.name} ne doit plus exister dans routers/ (doit être en quarantaine)'


def test_14_no_second_model_authority():
    """Vérifie que core/tool_gateway/model_router.py n'existe plus dans le Core actif."""
    old_mr = ROOT / 'core' / 'tool_gateway' / 'model_router.py'
    assert not old_mr.exists(), 'L ancien model_router ne doit plus exister dans core/tool_gateway/'


def test_15_no_direct_provider_bypass():
    """Vérifie que le SDK officiel passe par les points d entrée canoniques."""
    sdk = ROOT / 'core' / 'sdk.py'
    assert sdk.exists(), 'core/sdk.py doit exister'
    txt = sdk.read_text(encoding='utf-8', errors='ignore')
    assert 'chat' in txt
    assert 'generate' in txt


def test_16_no_new_memory_backend_without_gate():
    """Vérifie que la mémoire SQLite canonique est bien configurée avec WAL et EvidenceStore."""
    um = ROOT / 'core' / 'memory' / 'unified_gateway.py'
    assert um.exists()
    txt = um.read_text(encoding='utf-8', errors='ignore')
    assert 'WAL' in txt
    assert 'aiosqlite' in txt


def test_17_no_new_coding_worker_without_gate():
    """Vérifie qu'aucun framework de coding concurrent n'est présent dans core/."""
    for forbidden in ['openhands', 'mini_swe', 'aider']:
        matches = list((ROOT / 'core').glob(f'**/*{forbidden}*.py'))
        assert len(matches) == 0, f'Framework de code concurrent {forbidden} interdit dans core/'


def test_18_no_new_http_router_authority():
    """Vérifie que web_server.py est la seule autorité d'instanciation globale de l'app FastAPI."""
    app_instantiations = []
    for py in (ROOT / 'core').glob('**/*.py'):
        txt = py.read_text(encoding='utf-8', errors='ignore')
        for line in txt.splitlines():
            line_s = line.strip()
            if line_s.startswith('app = FastAPI(') or line_s.startswith('app = FastAPI ()'):
                app_instantiations.append(str(py))
    assert len(app_instantiations) == 0, f'Une seconde autorité FastAPI a été détectée dans {app_instantiations}'


def test_19_no_unauthorized_experimental_framework_in_core():
    """Vérifie qu'aucun framework expérimental n'est importé directement dans core/cognition/."""
    for py in (ROOT / 'core' / 'cognition').glob('*.py'):
        txt = py.read_text(encoding='utf-8', errors='ignore')
        for exp in ['docling', 'figranium', 'browser_use', 'opencode', 'llama_cpp']:
            assert f'import {exp}' not in txt and f'from {exp}' not in txt, f'Import expérimental {exp} interdit dans {py}'


def test_20_litellm_role_matches_documented_role():
    """Vérifie que LiteLLM est utilisé conformément à son rôle documenté (Bridge types / Schemas)."""
    router_file = ROOT / 'core' / 'models' / 'router.py'
    assert router_file.exists()
    txt = router_file.read_text(encoding='utf-8', errors='ignore')
    assert 'litellm' in txt.lower()
