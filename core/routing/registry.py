"""
Registre canonique unifié des modèles.

ARCHITECTURE :
  - registry.py       : SOURCE UNIQUE (cloud + local) ← CE FICHIER
  - model_registry.py : hub d'API (rôles métier + compatibilité)
  - provider_specs.py : HTTP fetch + pricing

Ce fichier contient :
  - ModelSpec (cloud) + LocalModelSpec (local)
  - PROVIDERS : 5 providers cloud
  - LOCAL_MODELS : modèles Ollama
  - Helpers : all_models, all_local, get_model, ...

Pour ajouter un modèle :
  - Cloud : ajouter un ModelSpec dans PROVIDERS[provider].models
  - Local : ajouter un LocalModelSpec dans LOCAL_MODELS
Puis : python scripts/check_contracts.py
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ThinkingMethod = Literal["thinkingLevel", "thinkingBudget", "budget_tokens", "none"]
Level = Literal["off", "low", "medium", "high"]
ProviderName = Literal["gemini", "groq", "anthropic", "openai", "mistral"]
LocalRole = Literal[
    "FAST_LOCAL", "LOCAL", "LOCAL_CODING", "LOCAL_MINI",
    "LOCAL_THINKING", "LOCAL_AGENT", "VISION", "EMBEDDING",
    "GENERALIST", "REASONING",
]


# ============================================================
# SPECS CLOUD
# ============================================================

@dataclass(frozen=True)
class ModelSpec:
    """Spécification d'un modèle cloud."""
    id: str
    provider: ProviderName
    family: str
    thinking_method: ThinkingMethod = "none"
    thinking_levels: tuple[Level, ...] = ()
    is_free: bool = False
    is_vision: bool = False
    is_image_gen: bool = False
    fallback_for: tuple[str, ...] = ()
    deprecated_at: str | None = None
    replaced_by: str | None = None

    def __post_init__(self):
        if self.thinking_method != "none" and not self.thinking_levels:
            raise ValueError(f"{self.id}: thinking_method défini mais levels vides")
        if self.deprecated_at and not self.replaced_by:
            raise ValueError(f"{self.id}: deprecated sans replaced_by")


@dataclass(frozen=True)
class ProviderSpec:
    """Spécification d'un provider cloud."""
    name: ProviderName
    base_url: str
    default_model: str
    fallback_models: tuple[str, ...] = ()
    api_key_env: tuple[str, ...] = ()
    models: tuple[ModelSpec, ...] = field(default_factory=tuple)


# ============================================================
# SPECS LOCAL
# ============================================================

@dataclass(frozen=True)
class LocalModelSpec:
    """Spécification d'un modèle Ollama local."""
    id: str
    role: LocalRole
    size_gb: float = 0.0
    family: str = ""
    thinking: bool = False
    vision: bool = False
    embedding: bool = False
    notes: str = ""


# ============================================================
# DÉCLARATIONS CLOUD
# ============================================================

GEMINI_MODELS = (
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
# DÉCLARATIONS LOCAL
# ============================================================

LOCAL_MODELS: tuple[LocalModelSpec, ...] = (
    LocalModelSpec("qwen3.5-mtp:4b", role="FAST_LOCAL", size_gb=3.0,
                   family="qwen3.5", notes="Rapide, usage courant"),
    LocalModelSpec("phi4-mini:latest", role="LOCAL_MINI", size_gb=2.5,
                   family="phi4", notes="Mini Microsoft"),
    LocalModelSpec("ministral-3b:latest", role="FAST_LOCAL", size_gb=2.1,
                   family="ministral", notes="Mistral 3B rapide"),
    LocalModelSpec("qwen3.5:9b", role="GENERALIST", size_gb=6.6,
                   family="qwen3.5", thinking=True),
    LocalModelSpec("granite4.2:8b", role="GENERALIST", size_gb=5.3,
                   family="granite4.2", notes="IBM Granite"),
    LocalModelSpec("granite4.2:3b", role="GENERALIST", size_gb=2.2,
                   family="granite4.2"),
    LocalModelSpec("maternion/ling-3.0-tiny:8b", role="GENERALIST", size_gb=5.3,
                   family="ling-3.0"),
    LocalModelSpec("qwen2.5-coder:7b-instruct-q4_K_M", role="LOCAL_CODING",
                   size_gb=4.7, family="qwen2.5-coder"),
    LocalModelSpec("deepseek-r1:7b", role="REASONING", size_gb=4.7,
                   family="deepseek-r1", thinking=True),
    LocalModelSpec("hermes3:8b", role="LOCAL_AGENT", size_gb=4.7,
                   family="hermes3"),
    LocalModelSpec("minicpm5-2b:latest", role="VISION", size_gb=1.6,
                   family="minicpm", vision=True),
    LocalModelSpec("minicpm-v:8b", role="VISION", size_gb=5.5,
                   family="minicpm", vision=True),
    LocalModelSpec("huihui_ai/gemma-4-abliterated:12b", role="GENERALIST",
                   size_gb=7.6, family="gemma-4", notes="Variante abliterated"),
    LocalModelSpec("bge-m3:latest", role="EMBEDDING", size_gb=1.2,
                   family="bge-m3", embedding=True),
)


# ============================================================
# HELPERS CLOUD
# ============================================================

def all_models() -> list[ModelSpec]:
    """Tous les modèles cloud actifs (non dépréciés)."""
    return [m for p in PROVIDERS.values() for m in p.models if not m.deprecated_at]


def all_deprecated() -> list[ModelSpec]:
    """Tous les modèles cloud dépréciés."""
    return [m for p in PROVIDERS.values() for m in p.models if m.deprecated_at]


def get_model(model_id: str) -> ModelSpec | None:
    for p in PROVIDERS.values():
        for m in p.models:
            if m.id == model_id:
                return m
    return None


def get_provider(name: str) -> ProviderSpec | None:
    return PROVIDERS.get(name)


def resolve_deprecated(model_id: str) -> str:
    m = get_model(model_id)
    if m and m.deprecated_at and m.replaced_by:
        return m.replaced_by
    return model_id


def models_with_thinking(method: ThinkingMethod) -> list[ModelSpec]:
    return [m for m in all_models() if m.thinking_method == method]


# ============================================================
# HELPERS LOCAL
# ============================================================

def all_local() -> list[LocalModelSpec]:
    """Tous les modèles locaux (hors embeddings)."""
    return [m for m in LOCAL_MODELS if not m.embedding]


def all_embeddings() -> list[LocalModelSpec]:
    return [m for m in LOCAL_MODELS if m.embedding]


def get_local(model_id: str) -> LocalModelSpec | None:
    for m in LOCAL_MODELS:
        if m.id == model_id:
            return m
    return None


def local_by_role(role: LocalRole) -> list[LocalModelSpec]:
    return [m for m in LOCAL_MODELS if m.role == role]


def local_thinking_capable() -> dict[str, dict]:
    """Format compatible avec THINKING_CAPABLE (local uniquement)."""
    return {
        m.id: {"method": "reasoning", "levels": ["off", "on"]}
        for m in LOCAL_MODELS
        if m.thinking
    }


def default_local() -> str:
    fast = local_by_role("FAST_LOCAL")
    if not fast:
        raise RuntimeError("Aucun modèle FAST_LOCAL déclaré")
    return fast[0].id
