"""
E-ZZIO — Settings utilisateur (toggle thinking, préférences).
État en mémoire + persistance JSON optionnelle.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

# FALLBACK_MAP
# Politique de fallback par provider. Si le modele choisi par l'utilisateur
# echoue (exception ou reponse vide), on bascule sur le modele cible ci-dessous
# et on signale la substitution via response.fallback_notice.
FALLBACK_MAP: dict[str, str] = {
    "groq":       "gemini-3.5-flash",
    "openrouter": "gemini-3.5-flash",
    "nvidia":     "gemini-3.5-flash",
    "ollama":     "gemini-3.5-flash",
    "gemini":     "gemini-3.5-flash",
}


router = APIRouter(prefix="/api/settings", tags=["settings"])

# ----------------------------------------------------------------------------
# Persistance JSON
# ----------------------------------------------------------------------------
_STATE_FILE = Path(__file__).parent.parent / "state" / "settings.json"

_DEFAULT_STATE: dict[str, Any] = {
    "thinking_enabled": False,
    "thinking_level": "off",
}


def _load_state() -> dict[str, Any]:
    if _STATE_FILE.exists():
        try:
            with open(_STATE_FILE, encoding="utf-8") as f:
                return {**_DEFAULT_STATE, **json.load(f)}
        except Exception:
            pass
    return dict(_DEFAULT_STATE)


def _save_state(state: dict[str, Any]) -> None:
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


_state = _load_state()


# ----------------------------------------------------------------------------
# Modèles Pydantic
# ----------------------------------------------------------------------------
class ThinkingSettings(BaseModel):
    enabled: bool
    level: str = Field(default="off", description="off | low | medium | high")


# ----------------------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------------------
@router.get("/thinking")
async def get_thinking() -> dict[str, Any]:
    return dict(_state)


@router.post("/thinking")
async def set_thinking(settings: ThinkingSettings) -> dict[str, Any]:
    if settings.level not in ("off", "low", "medium", "high"):
        return {"ok": False, "error": "level doit être off/low/medium/high"}

    _state["thinking_enabled"] = settings.enabled
    _state["thinking_level"] = settings.level if settings.enabled else "off"
    _save_state(_state)

    return {"ok": True, "state": dict(_state)}
