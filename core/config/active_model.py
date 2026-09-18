"""
core/config/active_model.py — Source unique de vérité pour le modèle actif.

Lit/écrit runtime/active_model.json. Tous les providers et routers
doivent importer get_active_model() / set_active_model() depuis ici.
"""
import json
from pathlib import Path

# Chemin du fichier de persistance
_RUNTIME_DIR = Path(__file__).resolve().parents[2] / "runtime"
_ACTIVE_MODEL_FILE = _RUNTIME_DIR / "active_model.json"

# Modèle par défaut (fallback si rien n'est configuré)
DEFAULT_MODEL: dict[str, str] = {
    "provider": "gemini",
    "model_id": "gemini-3.6-flash",
    "display_name": "Gemini 3.6 Flash",
}


def get_active_model() -> dict[str, str]:
    """Retourne le modèle actif (depuis le fichier ou défaut)."""
    try:
        if _ACTIVE_MODEL_FILE.exists():
            with open(_ACTIVE_MODEL_FILE, encoding="utf-8") as f:
                data = json.load(f)
                if "provider" in data and "model_id" in data:
                    return data
    except Exception as e:
        print(f"[active_model] Erreur lecture : {e}")
    return dict(DEFAULT_MODEL)


def set_active_model(provider: str, model_id: str, display_name: str | None = None) -> dict[str, str]:
    """Définit le modèle actif et le persiste."""
    _RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "provider": provider,
        "model_id": model_id,
        "display_name": display_name or model_id,
    }
    with open(_ACTIVE_MODEL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data


def get_active_gemini_model() -> str:
    """Helper : retourne le model_id Gemini actif (ou défaut)."""
    m = get_active_model()
    if m.get("provider") == "gemini":
        return m.get("model_id", DEFAULT_MODEL["model_id"])
    return DEFAULT_MODEL["model_id"]
