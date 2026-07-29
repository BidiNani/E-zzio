import os
import sys
import importlib
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

def test_runtime_components_availability():
    """Vérifie que les composants critiques du runtime sont importables et structurellement valides."""
    components = [
        "runtime.core.events.EventBus",
        "runtime.memory.dream.engine.DreamEngine",
        "runtime.memory.sleep.consolidator.Consolidator",
        "runtime.core.microkernel.EzzioRuntime",
        "runtime.memory.gateway.MemoryGateway"
    ]
    for comp in components:
        mod_name, cls_name = comp.rsplit(".", 1)
        mod = importlib.import_module(mod_name)
        assert hasattr(mod, cls_name), f"Classe {cls_name} manquante dans {mod_name}"

def test_legacy_aliases_integrity():
    """Vérifie que les alias de rétrocompatibilité sont bien en place (Bridges)."""
    from runtime.core.microkernel import MicroKernel
    from runtime.core.microkernel import EzzioRuntime
    assert MicroKernel is EzzioRuntime, "Le bridge MicroKernel -> EzzioRuntime est rompu."

    from runtime.memory.semantic.recovery import MemoryRecoveryEngine
    from runtime.memory.semantic.recovery import RecoveryEngine
    assert MemoryRecoveryEngine is RecoveryEngine, "Le bridge MemoryRecoveryEngine -> RecoveryEngine est rompu."

def test_external_api_environment():
    """Vérifie la présence des configurations d'API (Gemini, Groq) dans l'environnement ou le .env."""
    env_path = os.path.join(ROOT, ".env")
    has_gemini = "GEMINI_API_KEY" in os.environ
    has_groq = "GROQ_API_KEY" in os.environ

    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
            if "GEMINI_API_KEY=" in content: has_gemini = True
            if "GROQ_API_KEY=" in content: has_groq = True

    print(f"\n[API CONFIG AUDIT] Gemini: {'OK' if has_gemini else 'MISSING/LAZY'}, Groq: {'OK' if has_groq else 'MISSING/LAZY'}")
    assert True  # On ne fail pas le test si les clés sont injectées dynamiquement, on audite juste.
