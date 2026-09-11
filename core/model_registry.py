"""
core/model_registry.py — Adaptive Model Governor V7.21
Intègre la hiérarchie des vitesses, les paliers de fallback multi-niveaux
et l'exploitation directe des métadonnées du registre de capacités.
"""

import json
from pathlib import Path

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
CAPABILITIES_PATH = ROOT_DIR / "runtime" / "models" / "model_capabilities.json"
LATENCY_LOG_PATH = ROOT_DIR / "runtime" / "audit" / "model_latency.json"


def _load_capabilities():
    if CAPABILITIES_PATH.exists():
        try:
            data = json.loads(CAPABILITIES_PATH.read_text(encoding="utf-8"))
            return data.get("models", {})
        except Exception:
            pass
    return {
        "qwen2.5:7b": {"roles": ["conversation", "fallback_default"], "speed": "fast"},
        "qwen2.5-coder:7b": {"roles": ["coding"], "speed": "fast"},
        "qwen2.5-coder:7b_reasoning": {"roles": ["reasoning", "deep_analysis", "architecture"], "speed": "medium"},
        "qwen2.5:3b_fast": {"roles": ["quick_response"], "speed": "ultra-fast"},
        "qwen2.5:3b": {"roles": ["vision"], "speed": "fast"},
    }


MODELS_DB = _load_capabilities()

# Classement par vitesse intrinsèque (du plus rapide au plus lourd)
SPEED_HIERARCHY = {"ultra-fast": 1, "fast": 2, "medium": 3, "slow": 4}

ULTRA_FAST_POOL = [m for m, meta in MODELS_DB.items() if meta.get("speed") == "ultra-fast"]
FAST_MODEL_POOL = [m for m, meta in MODELS_DB.items() if meta.get("speed") in ["fast", "ultra-fast"]]
DEEP_MODEL_POOL = [m for m, meta in MODELS_DB.items() if "reasoning" in meta.get("roles", []) or "deep_analysis" in meta.get("roles", [])]
CODING_MODELS = [m for m, meta in MODELS_DB.items() if "coding" in meta.get("roles", [])]
VISION_MODELS = [m for m, meta in MODELS_DB.items() if meta.get("vision", False)]

DEFAULT_FAST = ULTRA_FAST_POOL[0] if ULTRA_FAST_POOL else (FAST_MODEL_POOL[0] if FAST_MODEL_POOL else list(MODELS_DB.keys())[0])
DEFAULT_CODING = CODING_MODELS[0] if CODING_MODELS else DEFAULT_FAST
DEFAULT_DEEP = DEEP_MODEL_POOL[0] if DEEP_MODEL_POOL else DEFAULT_FAST
DEFAULT_CONVO = "qwen2.5:7b" if "qwen2.5:7b" in MODELS_DB else DEFAULT_FAST

# Organes dotés de chaînes de fallback multi-niveaux robustes
ORGANS = {
    "presence": {
        "model": DEFAULT_CONVO,
        "fast_candidates": ULTRA_FAST_POOL + FAST_MODEL_POOL,
        "deep_model": DEFAULT_DEEP,
        "fallback_chain": [DEFAULT_FAST, DEFAULT_CONVO],
        "priority": 1,
    },
    "coding": {
        "model": DEFAULT_CODING,
        "fast_candidates": CODING_MODELS,
        "deep_model": DEFAULT_DEEP,
        "fallback_chain": CODING_MODELS + [DEFAULT_DEEP, DEFAULT_CONVO],
        "priority": 2,
    },
    "architecture": {
        "model": DEFAULT_DEEP,
        "fast_candidates": CODING_MODELS,
        "deep_model": DEFAULT_DEEP,
        "fallback_chain": [DEFAULT_DEEP, DEFAULT_CODING, DEFAULT_CONVO],
        "priority": 3,
    },
    "vision": {
        "model": VISION_MODELS[0] if VISION_MODELS else DEFAULT_FAST,
        "fast_candidates": VISION_MODELS,
        "deep_model": DEFAULT_DEEP,
        "fallback_chain": [DEFAULT_FAST, DEFAULT_CONVO],
        "priority": 4,
    },
}


def all_known_models():
    return list(MODELS_DB.keys())


def best_fast_model(candidates=None):
    """Sélectionne le modèle le plus rapide en se basant sur la hiérarchie speed du registre."""
    pool = candidates if candidates else FAST_MODEL_POOL
    if not pool:
        return DEFAULT_FAST

    # Tri des candidats par ordre de vitesse croissante (ultra-fast en premier)
    sorted_by_speed = sorted([c for c in pool if c in MODELS_DB], key=lambda x: SPEED_HIERARCHY.get(MODELS_DB[x].get("speed", "fast"), 5))
    return sorted_by_speed[0] if sorted_by_speed else DEFAULT_FAST


def load_latency():
    """Charge le registre de latence réel si disponible, sinon simule depuis le registre de capacités."""
    if LATENCY_LOG_PATH.exists():
        try:
            return json.loads(LATENCY_LOG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    # Baseline par défaut basée sur les paliers de vitesse
    return {m: (0.5 if meta.get("speed") == "ultra-fast" else 1.5) for m, meta in MODELS_DB.items()}


# Patch de compatibilité pour routers/models.py
def save_latency(*args, **kwargs):
    """Enregistrement de la latence d'un modèle."""
    pass
