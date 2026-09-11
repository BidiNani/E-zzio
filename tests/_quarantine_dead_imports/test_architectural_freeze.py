"""Gel architectural : invariants dont la violation = dérive. Léger, déterministe.

Toute modification faisant échouer ce fichier est une dérive architecturale :
STOP, analyser, restaurer ou justifier explicitement avant d'intégrer.
"""
from core.routing.model_registry import canonical_model_registry, ModelQualificationStatus


def test_freeze_primary_is_gemini_37_flash():
    rec = canonical_model_registry.get("gemini/gemini-3.7-flash")
    assert rec is not None
    assert rec.qualification_status == ModelQualificationStatus.QUALIFIED


def test_freeze_single_routing_authority():
    from core.agent.coder_federation import coder_federation_router
    import core.ezzio_master as m

    assert m.ezzio_master.federation_router is coder_federation_router


def test_freeze_vault_first_on_canonical_providers():
    import inspect
    for mod in ("core.providers.gemini_provider", "core.providers.groq_provider",
                "core.providers.openrouter_provider", "core.providers.nvidia_nim_provider"):
        src = inspect.getsource(__import__(mod, fromlist=["x"]))
        assert "unified_vault" in src or "key_vault" in src, mod


def test_freeze_no_second_microkernel():
    import os
    assert not os.path.exists("recovery/certified_state/microkernel.py")
    assert not os.path.exists("legacy_archive/recovery/certified_state/microkernel.py")


def test_freeze_rejected_never_qualified():
    for mid in ("local/qwen3:8b", "local/qwen3.5:9b", "local/qwen2.5-coder:7b",
                "local/deepseek-r1:8b", "local/llava:13b"):
        rec = canonical_model_registry.get(mid)
        assert rec is not None
        assert rec.qualification_status == ModelQualificationStatus.REJECTED, mid


def test_freeze_canonical_api_is_8001():
    src = open("web_server.py", encoding="utf-8").read()
    assert "port=8001" in src
    for mod in ("app.py", "runtime/external/ezzio_app.py"):
        assert mod  # dormants connus, non montés (voir dormancy.py)
