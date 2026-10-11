"""Gouvernance du routage explicite (#3) — la cible doit être canonique, sinon FAIL-CLOSED.

`ModelRouter.select_engine(model_target=...)` ne doit accepter QUE des cibles
présentes dans la source unique `core.routing.registry` (providers + modèles).
Toute cible inconnue doit être refusée en FAIL-CLOSED (aucun routage arbitraire).
"""
from __future__ import annotations

from core.cognition.model_router import ModelRouter


def _route(target: str, **kw):
    return ModelRouter().select_engine(model_target=target, **kw)


def test_explicit_canonical_provider_model_resolves():
    r = _route("groq/llama-3.3-70b")
    assert r["provider"] == "groq"
    assert r["model"] == "groq/llama-3.3-70b"
    assert r["role"] == "EXPLICIT_TARGET"


def test_explicit_bare_provider_uses_canonical_default_model():
    r = _route("gemini")
    assert r["provider"] == "gemini"
    # modèle par défaut du provider canonique
    assert r["model"]


def test_explicit_registered_model_resolves():
    r = _route("gemini-3.5-flash")
    assert r["provider"] == "gemini"
    assert r["model"] == "gemini-3.5-flash"


def test_explicit_local_token_resolves_to_ollama():
    r = _route("local")
    assert r["provider"] == "ollama"
    assert r["is_local"] is True


def test_unknown_model_target_fails_closed():
    r = _route("modele-inexistant-xyz")
    assert r["status"] == "FAIL_CLOSED"
    assert r["error"] == "UNKNOWN_MODEL_TARGET"


def test_unknown_provider_prefix_fails_closed():
    r = _route("foobar/model")
    assert r["status"] == "FAIL_CLOSED"
    assert r["error"] == "UNKNOWN_MODEL_TARGET"


def test_local_only_blocks_cloud_target():
    r = _route("groq/llama-3.3-70b", local_only=True)
    assert r["status"] == "FAIL_CLOSED"
    assert r["error"] == "LOCAL_ONLY_BLOCKS_CLOUD_TARGET"


def test_openrouter_provider_default_model_resolves():
    r = _route("openrouter")
    assert r["provider"] == "openrouter"
    assert r["model"]


def test_openrouter_namespaced_model_id_resolves():
    # Les ids OpenRouter contiennent un '/' : la validation se fait par id complet.
    r = _route("z-ai/glm-5.2:free")
    assert r["provider"] == "openrouter"
    assert r["model"] == "z-ai/glm-5.2:free"


def test_openrouter_unknown_model_fails_closed():
    r = _route("openrouter/not-a-real-model:free")
    assert r["status"] == "FAIL_CLOSED"
    assert r["error"] == "UNKNOWN_MODEL_TARGET"


def test_nvidia_provider_default_model_resolves():
    r = _route("nvidia")
    assert r["provider"] == "nvidia"
    assert r["model"].startswith("nvidia/")
