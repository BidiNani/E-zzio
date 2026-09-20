"""
Registre canonique des providers et de leurs modèles.

SOURCE UNIQUE DE VÉRITÉ — tout le code (routers, agents, providers)
doit lire ce fichier. Toute modification se propage automatiquement.

Pour ajouter un modèle :
  1. Ajouter une entrée ModelSpec dans PROVIDERS[provider].models
  2. Lancer `python scripts/check_contracts.py` pour valider
  3. Lancer `pytest tests/contracts/` pour les tests générés

Contrat strict :
  - thinking_method ∈ {thinkingLevel, thinkingBudget, budget_tokens, none}
  - levels ⊆ {off, low, medium, high}
  - family ∈ {gemini, groq, anthropic, openai, mistral, ...}
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ThinkingMethod = Literal["thinkingLevel", "thinkingBudget", "budget_tokens", "none"]
Level = Literal["off", "low", "medium", "high"]
ProviderName = Literal["gemini", "groq", "anthropic", "openai", "mistral"]


@dataclass(frozen=True)
class ModelSpec:
    """Spécification canonique d'un modèle."""
    id: str
    provider: ProviderName
    family: str                      # ex: "gemini-3.x", "claude-4", "llama-3"
    thinking_method: ThinkingMethod = "none"
    thinking_levels: tuple[Level, ...] = ()
    is_free: bool = False
    is_vision: bool = False
    is_image_gen: bool = False
    fallback_for: tuple[str, ...] = ()   # IDs de modèles dont celui-ci est fallback
    deprecated_at: str | None = None
    replaced_by: str | None = None

    def __post_init__(self):
        if self.thinking_method != "none" and not self.thinking_levels:
            raise ValueError(f"{self.id}: thinking_method défini mais levels vides")
        if self.deprecated_at and not self.replaced_by:
            raise ValueError(f"{self.id}: deprecated sans replaced_by")


@dataclass(frozen=True)
class ProviderSpec:
    """Spécification canonique d'un provider."""
    name: ProviderName
    base_url: str
    default_model: str
    fallback_models: tuple[str, ...] = ()
    api_key_env: tuple[str, ...] = ()
    models: tuple[ModelSpec, ...] = field(default_factory=tuple)


# ============================================================
# DÉCLARATIONS — à maintenir ici uniquement
# ============================================================

GEMINI_MODELS = (
    # Gemini 3.x — thinkingLevel (low/high seulement)
    ModelSpec("gemini-3.8-flash", "gemini", "gemini-3.x",
              thinking_method="thinkingLevel", thinking_levels=("low", "high"),
              is_free=True, is_vision=True),
    ModelSpec("gemini-3.7-flash", "gemini", "gemini-3.x",
              thinking_method="thinkingLevel", thinking_levels=("low", "high"),
              is_free=True, is_vision=True),
    ModelSpec("gemini-3.6-flash", "gemini", "gemini-3.x",
              thinking_method="thinkingLevel", thinking_levels=("low", "high"),
              is_free=True, is_vision=True),
    ModelSpec("gemini-3.5-flash", "gemini", "gemini-3.x",
              thinking_method="thinkingLevel", thinking_levels=("low", "high"),
              is_free=True, is_vision=True),
    ModelSpec("gemini-3.5-flash-lite", "gemini", "gemini-3.x",
              thinking_method="thinkingLevel", thinking_levels=("low", "high"),
              is_free=True, is_vision=True, fallback_for=("gemini-3.5-flash",)),
    # Gemini 2.5 dépréciés (conservés pour référence)
    ModelSpec("gemini-2.5-flash", "gemini", "gemini-2.5",
              thinking_method="thinkingBudget", thinking_levels=("off", "low", "medium", "high"),
              is_free=True, is_vision=True,
              deprecated_at="2026-09-20", replaced_by="gemini-3.5-flash-lite"),
    ModelSpec("gemini-2.5-flash-image", "gemini", "gemini-2.5",
              thinking_method="none", is_vision=True, is_image_gen=True,
              deprecated_at="2026-09-20", replaced_by="gemini-3.5-flash"),
)

GROQ_MODELS = (
    ModelSpec("groq/compound", "groq", "groq-compound",
              thinking_method="none", is_free=True),
    ModelSpec("groq/llama-3.3-70b", "groq", "llama-3",
              thinking_method="none", is_free=True),
)

ANTHROPIC_MODELS = (
    ModelSpec("anthropic/claude-3.7", "anthropic", "claude-3",
              thinking_method="budget_tokens", thinking_levels=("low", "medium", "high")),
    ModelSpec("anthropic/claude-sonnet-4", "anthropic", "claude-4",
              thinking_method="budget_tokens", thinking_levels=("low", "medium", "high")),
)

OPENAI_MODELS = (
    ModelSpec("openai/gpt-4o", "openai", "gpt-4",
              thinking_method="none", is_vision=True),
    ModelSpec("openai/gpt-4o-mini", "openai", "gpt-4",
              thinking_method="none", is_vision=True, is_free=True),
)

MISTRAL_MODELS = (
    ModelSpec("mistral/mistral-large", "mistral", "mistral-large",
              thinking_method="none"),
)


PROVIDERS: dict[ProviderName, ProviderSpec] = {
    "gemini": ProviderSpec(
        name="gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta/models",
        default_model="gemini-3.5-flash-lite",
        fallback_models=("gemini-3.6-flash", "gemini-3.8-flash"),
        api_key_env=("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        models=GEMINI_MODELS,
    ),
    "groq": ProviderSpec(
        name="groq",
        base_url="https://api.groq.com/openai/v1",
        default_model="groq/compound",
        api_key_env=("GROQ_API_KEY",),
        models=GROQ_MODELS,
    ),
    "anthropic": ProviderSpec(
        name="anthropic",
        base_url="https://api.anthropic.com/v1",
        default_model="anthropic/claude-sonnet-4",
        api_key_env=("ANTHROPIC_API_KEY",),
        models=ANTHROPIC_MODELS,
    ),
    "openai": ProviderSpec(
        name="openai",
        base_url="https://api.openai.com/v1",
        default_model="openai/gpt-4o-mini",
        api_key_env=("OPENAI_API_KEY",),
        models=OPENAI_MODELS,
    ),
    "mistral": ProviderSpec(
        name="mistral",
        base_url="https://api.mistral.ai/v1",
        default_model="mistral/mistral-large",
        api_key_env=("MISTRAL_API_KEY",),
        models=MISTRAL_MODELS,
    ),
}


# ============================================================
# HELPERS — utiliser partout dans le code
# ============================================================

def all_models() -> list[ModelSpec]:
    """Tous les modèles actifs (non dépréciés)."""
    return [m for p in PROVIDERS.values() for m in p.models if not m.deprecated_at]


def all_deprecated() -> list[ModelSpec]:
    """Tous les modèles dépréciés (pour migration)."""
    return [m for p in PROVIDERS.values() for m in p.models if m.deprecated_at]


def get_model(model_id: str) -> ModelSpec | None:
    """Retourne un ModelSpec par ID, ou None."""
    for p in PROVIDERS.values():
        for m in p.models:
            if m.id == model_id:
                return m
    return None


def get_provider(name: str) -> ProviderSpec | None:
    return PROVIDERS.get(name)


def resolve_deprecated(model_id: str) -> str:
    """Si le modèle est déprécié, retourne son remplaçant."""
    m = get_model(model_id)
    if m and m.deprecated_at and m.replaced_by:
        return m.replaced_by
    return model_id


def models_with_thinking(method: ThinkingMethod) -> list[ModelSpec]:
    return [m for m in all_models() if m.thinking_method == method]
