"""
Tests de contrat AUTOMATIQUES pour tous les providers.

Chaque modèle déclaré dans providers_registry.py est testé :
  - Payload thinking correct selon son thinking_method
  - Cohérence provider <-> modèle
  - Présence dans le registre

Ajouter un modèle = les tests suivent.
"""
from __future__ import annotations

import pytest

from core.routing.registry import (
    PROVIDERS,
    all_deprecated,
    all_models,
    get_model,
)

ALL_ACTIVE = all_models()
ALL_DEPRECATED = all_deprecated()


# ============================================================
# Tests génériques sur tous les modèles actifs
# ============================================================

@pytest.mark.parametrize("model", ALL_ACTIVE, ids=lambda m: m.id)
def test_model_id_unique(model):
    """Chaque ID est unique."""
    matches = [m for m in ALL_ACTIVE if m.id == model.id]
    assert len(matches) == 1


@pytest.mark.parametrize("model", ALL_ACTIVE, ids=lambda m: m.id)
def test_model_has_valid_provider(model):
    """Le provider du modèle existe."""
    assert model.provider in PROVIDERS


@pytest.mark.parametrize("model", ALL_ACTIVE, ids=lambda m: m.id)
def test_thinking_coherence(model):
    """Méthode thinking et levels cohérents."""
    if model.thinking_method == "none":
        assert not model.thinking_levels, f"{model.id}: thinking_method=none mais levels présents"
    else:
        assert model.thinking_levels, f"{model.id}: thinking_method={model.thinking_method} mais levels vides"
        for lvl in model.thinking_levels:
            assert lvl in ("off", "low", "medium", "high")


@pytest.mark.parametrize("model", ALL_ACTIVE, ids=lambda m: m.id)
def test_gemini_3x_uses_low_high(model):
    """Gemini 3.x doit utiliser thinkingLevel avec low/high uniquement."""
    if model.provider == "gemini" and "3." in model.family:
        if model.thinking_method != "none":
            assert model.thinking_method == "thinkingLevel", (
                f"{model.id}: Gemini 3.x doit utiliser thinkingLevel"
            )
            invalid = [lvl for lvl in model.thinking_levels if lvl not in ("low", "high")]
            assert not invalid, f"{model.id}: levels invalides {invalid}"


# ============================================================
# Tests sur les dépréciés
# ============================================================

@pytest.mark.parametrize("model", ALL_DEPRECATED, ids=lambda m: m.id)
def test_deprecated_has_replacement(model):
    """Tout modèle déprécié a un remplaçant valide."""
    assert model.replaced_by, f"{model.id}: déprécié sans replaced_by"
    replacement = get_model(model.replaced_by)
    assert replacement, f"{model.id}: replaced_by={model.replaced_by} introuvable"
    assert not replacement.deprecated_at, (
        f"{model.id}: remplacé par un autre modèle déprécié"
    )


# ============================================================
# Tests par provider
# ============================================================

@pytest.mark.parametrize("provider_name", list(PROVIDERS.keys()))
def test_provider_has_default_model(provider_name):
    """Le default_model du provider existe dans ses models."""
    p = PROVIDERS[provider_name]
    ids = {m.id for m in p.models}
    assert p.default_model in ids, (
        f"{provider_name}: default_model={p.default_model} absent"
    )


@pytest.mark.parametrize("provider_name", list(PROVIDERS.keys()))
def test_provider_has_api_key_env(provider_name):
    """Chaque provider déclare ses variables d'environnement."""
    p = PROVIDERS[provider_name]
    assert p.api_key_env, f"{provider_name}: pas d'api_key_env déclaré"


@pytest.mark.parametrize("provider_name", list(PROVIDERS.keys()))
def test_provider_base_url_https(provider_name):
    """Les URLs doivent être HTTPS."""
    p = PROVIDERS[provider_name]
    assert p.base_url.startswith("https://"), (
        f"{provider_name}: base_url non HTTPS"
    )
