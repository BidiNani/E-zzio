"""Gel architectural : invariants dont la violation = dérive. Léger, déterministe.

Toute modification faisant échouer ce fichier est une dérive architecturale :
STOP, analyser, restaurer ou justifier explicitement avant d'intégrer.
"""
from core.routing.model_registry import canonical_model_registry, ModelQualificationStatus


def test_freeze_primary_is_gemini_37_flash():
    rec = canonical_model_registry.get("gemini-3.7-flash")
    assert rec is not None
    assert rec.qualification_status == ModelQualificationStatus.QUALIFIED


def test_freeze_single_routing_authority():
    from core.cognition.model_router import ModelRouter
    router = ModelRouter()
    res = router.select_engine(task_type="general", is_mission=True)
    assert res["model"] == "gemini-3.8-flash"


def test_freeze_vault_first_on_canonical_providers():
    import inspect
    for mod in ("core.providers.gemini_provider", "core.providers.groq_provider",
                "core.providers.ollama_provider"):
        src = inspect.getsource(__import__(mod, fromlist=["x"]))
        assert "secrets_loader" in src or "get_api_key" in src or "os.getenv" in src, mod


def test_freeze_no_second_microkernel():
    import os
    assert not os.path.exists("recovery/certified_state/microkernel.py")
    assert not os.path.exists("legacy_archive/recovery/certified_state/microkernel.py")


def test_freeze_rejected_never_qualified():
    for mid in ("local/qwen3:8b", "local/qwen3.5:9b"):
        rec = canonical_model_registry.get(mid)
        assert rec is None or rec.qualification_status != ModelQualificationStatus.QUALIFIED


def test_freeze_canonical_api_is_8001():
    src = open("web_server.py", encoding="utf-8").read()
    assert "web_server.py" in src
