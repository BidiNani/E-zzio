"""
Registre des modèles locaux (Ollama).

SOURCE UNIQUE DE VÉRITÉ pour les modèles locaux. Les modèles cloud
sont dans providers_registry.py — les deux registres coexistent car
leurs sémantiques sont différentes :

  - Cloud : API key, quota, pricing, dépréciation distante
  - Local : installé/désinstallé via `ollama pull/rm`, pas d'API key

Pour synchroniser avec Ollama :
    python scripts/sync_local_models.py

Pour vérifier la cohérence registre <-> Ollama :
    python -m pytest tests/contracts/test_local_registry.py
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

LocalRole = Literal[
    "FAST_LOCAL", "LOCAL", "LOCAL_CODING", "LOCAL_MINI",
    "LOCAL_THINKING", "LOCAL_AGENT", "VISION", "EMBEDDING",
    "GENERALIST", "REASONING",
]


@dataclass(frozen=True)
class LocalModelSpec:
    """Spécification d'un modèle local Ollama."""
    id: str
    role: LocalRole
    size_gb: float = 0.0
    family: str = ""
    thinking: bool = False
    vision: bool = False
    embedding: bool = False
    notes: str = ""


# ============================================================
# DÉCLARATIONS — à synchroniser avec `ollama list`
# ============================================================

LOCAL_MODELS: tuple[LocalModelSpec, ...] = (
    # --- Fast / mini ---
    LocalModelSpec(
        "qwen3.5-mtp:4b", role="FAST_LOCAL", size_gb=3.0,
        family="qwen3.5", notes="Rapide, usage courant",
    ),
    LocalModelSpec(
        "phi4-mini:latest", role="LOCAL_MINI", size_gb=2.5,
        family="phi4", notes="Mini Microsoft",
    ),
    LocalModelSpec(
        "ministral-3b:latest", role="FAST_LOCAL", size_gb=2.1,
        family="ministral", notes="Mistral 3B rapide",
    ),

    # --- Généralistes ---
    LocalModelSpec(
        "qwen3.5:9b", role="GENERALIST", size_gb=6.6,
        family="qwen3.5", thinking=True,
    ),
    LocalModelSpec(
        "granite4.2:8b", role="GENERALIST", size_gb=5.3,
        family="granite4.2", notes="IBM Granite",
    ),
    LocalModelSpec(
        "granite4.2:3b", role="GENERALIST", size_gb=2.2,
        family="granite4.2",
    ),
    LocalModelSpec(
        "maternion/ling-3.0-tiny:8b", role="GENERALIST", size_gb=5.3,
        family="ling-3.0",
    ),

    # --- Coding ---
    LocalModelSpec(
        "qwen2.5-coder:7b-instruct-q4_K_M", role="LOCAL_CODING", size_gb=4.7,
        family="qwen2.5-coder",
    ),

    # --- Raisonnement ---
    LocalModelSpec(
        "deepseek-r1:7b", role="REASONING", size_gb=4.7,
        family="deepseek-r1", thinking=True,
    ),
    LocalModelSpec(
        "nemotron-3-nano:4b", role="LOCAL_THINKING", size_gb=0.0,
        family="nemotron", thinking=True,
        notes="Déclaré mais pas dans ollama list actuel",
    ),

    # --- Agent ---
    LocalModelSpec(
        "hermes3:8b", role="LOCAL_AGENT", size_gb=4.7,
        family="hermes3",
    ),

    # --- Vision ---
    LocalModelSpec(
        "minicpm5-2b:latest", role="VISION", size_gb=1.6,
        family="minicpm", vision=True,
    ),
    LocalModelSpec(
        "minicpm-v:8b", role="VISION", size_gb=5.5,
        family="minicpm", vision=True,
    ),

    # --- Uncensored / spécialisé ---
    LocalModelSpec(
        "huihui_ai/gemma-4-abliterated:12b", role="GENERALIST", size_gb=7.6,
        family="gemma-4", notes="Variante abliterated",
    ),

    # --- Embeddings ---
    LocalModelSpec(
        "bge-m3:latest", role="EMBEDDING", size_gb=1.2,
        family="bge-m3", embedding=True,
    ),
)


# ============================================================
# HELPERS
# ============================================================

def all_local() -> list[LocalModelSpec]:
    """Tous les modèles locaux (hors embeddings)."""
    return [m for m in LOCAL_MODELS if not m.embedding]


def all_embeddings() -> list[LocalModelSpec]:
    """Modèles d'embedding uniquement."""
    return [m for m in LOCAL_MODELS if m.embedding]


def get_local(model_id: str) -> LocalModelSpec | None:
    """Retourne un LocalModelSpec par ID, ou None."""
    for m in LOCAL_MODELS:
        if m.id == model_id:
            return m
    return None


def by_role(role: LocalRole) -> list[LocalModelSpec]:
    """Modèles avec un rôle donné."""
    return [m for m in LOCAL_MODELS if m.role == role]


def thinking_capable() -> dict[str, dict]:
    """Format compatible avec THINKING_CAPABLE."""
    return {
        m.id: {"method": "reasoning", "levels": ["off", "on"]}
        for m in LOCAL_MODELS
        if m.thinking
    }


def default_local() -> str:
    """Modèle local par défaut (rôle FAST_LOCAL)."""
    fast = by_role("FAST_LOCAL")
    if not fast:
        raise RuntimeError("Aucun modèle FAST_LOCAL déclaré")
    return fast[0].id
