"""Contrats architecturaux XL — violations = dérive, CI FAILURE."""
import ast


def _src(path):
    return open(path, encoding="utf-8").read()


def test_master_cannot_access_credentials_directly():
    tree = ast.parse(_src("core/ezzio_master.py"))
    mods = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.module:
            mods.add(n.module)
        elif isinstance(n, ast.Import):
            mods.update(a.name for a in n.names)
    assert not any("vault" in m or "secret" in m.lower() for m in mods), mods
    assert "API_KEY" not in _src("core/ezzio_master.py")
    assert "getenv" not in _src("core/ezzio_master.py")


def test_master_cannot_bypass_provider_governance():
    src = _src("core/ezzio_master.py")
    assert "federation_router.execute_task" in src
    assert ".generate(" not in src  # jamais d'appel provider direct


def test_providers_cannot_choose_models():
    import glob
    for path in glob.glob("core/providers/*.py"):
        src = _src(path)
        assert "coder_federation" not in src, path
        assert "canonical_model_registry" not in src, path
        assert "resolve_candidates" not in src, path


def test_registry_cannot_execute():
    src = _src("core/routing/model_registry.py")
    for token in ("httpx", "requests.", "urlopen", "generate(", "os.getenv"):
        assert token not in src, token


def test_channel_cannot_execute_business_logic():
    import glob
    for path in glob.glob("core/integrations/discord/*.py"):
        src = _src(path)
        assert ".generate(" not in src, path
        assert "coder_federation" not in src, path


def test_tool_cannot_self_authorize():
    src = _src("core/agent/tools_registry.py")
    assert "guard.evaluate_intent" in src
    assert src.count("guard.evaluate_intent") >= 2  # skills + outils de base


def test_self_healing_cannot_bypass_policy():
    for path in ("core/ezzio_master.py", "core/agent/coder_federation.py",
                 "web_server.py", "routers/master.py"):
        try:
            src = _src(path)
        except FileNotFoundError:
            continue
        assert "SelfHealingEngine" not in src, path
        assert "self_healing_engine" not in src, path
