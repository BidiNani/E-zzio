"""
Tests unitaires pour le Registre Canonique de Modèles E-ZzIO (Phase 6C).
"""
import pytest
from core.providers.base_provider import CostClass
from core.routing.model_registry import (
    CanonicalModelRegistry,
    CanonicalModelRecord,
    ModelSource,
    LatencyTier,
    ModelQualificationStatus,
    canonical_model_registry,
)


def test_registry_initialization_and_singleton():
    reg = canonical_model_registry
    assert isinstance(reg, CanonicalModelRegistry)
    active = reg.list_models(qualified_only=False)
    dormant = reg.list_models(qualified_only=False, include_disabled=True)
    assert len(dormant) >= 20
    assert len(dormant) - len(active) == 10  # 10 entrées NVIDIA désactivées


def test_all_sources_represented():
    reg = canonical_model_registry
    sources = {m.source for m in reg.list_models(qualified_only=False)}
    assert ModelSource.LOCAL in sources
    assert ModelSource.GEMINI in sources
    assert ModelSource.GROQ in sources
    assert ModelSource.NVIDIA not in sources
    dormant_sources = {m.source for m in reg.list_models(qualified_only=False, include_disabled=True)}
    assert ModelSource.NVIDIA in dormant_sources


def test_no_duplicate_model_ids():
    reg = CanonicalModelRegistry()
    model_ids = [m.model_id for m in reg.list_models(qualified_only=False)]
    assert len(model_ids) == len(set(model_ids)), "Doublons détectés dans le registre"


def test_model_qualification_statuses():
    reg = canonical_model_registry
    # Tous les modèles actifs doivent être QUALIFIED ou QUALIFIED_WITH_LIMITATIONS
    for model in reg.list_models(qualified_only=True):
        assert model.qualification_status in (
            ModelQualificationStatus.QUALIFIED,
            ModelQualificationStatus.QUALIFIED_WITH_LIMITATIONS,
        )


def test_nvidia_models_match_phase_5c():
    # NVIDIA désactivé : 10 entrées conservées mais exclues par défaut.
    reg = canonical_model_registry
    nvidia_models = reg.list_models(source=ModelSource.NVIDIA, qualified_only=False)
    assert nvidia_models == []
    dormant = reg.list_models(source=ModelSource.NVIDIA, qualified_only=False,
                              include_disabled=True)
    assert len(dormant) == 10
    assert all(m.enabled is False for m in dormant)

    # 6 ex-QUALIFIED désormais tous désactivés (aucun routable).
    qualified = [m for m in dormant
                 if m.qualification_status == ModelQualificationStatus.QUALIFIED]
    assert len(qualified) == 6
    assert all(m.enabled is False for m in qualified)

    # 4 QUALIFIED_WITH_LIMITATIONS dormants (données historiques conservées).
    with_limits = [m.model_id for m in dormant
                   if m.qualification_status == ModelQualificationStatus.QUALIFIED_WITH_LIMITATIONS]
    assert len(with_limits) == 4
    assert "nvidia/llama-3.2-11b-vision-instruct" in with_limits
    assert "nvidia/qwen2.5-coder-32b-instruct" in with_limits


def test_fallback_chain_resolution():
    reg = canonical_model_registry
    # Fallback pour gemini-3.7-flash
    chain = reg.get_fallback_chain("gemini/gemini-3.7-flash")
    assert len(chain) >= 1
    assert any("gemini-3.5-flash" in m.model_id for m in chain)

    # Modèle inexistant
    assert reg.get_fallback_chain("nonexistent/model") == []


def test_resolve_best_model_capability():
    reg = canonical_model_registry
    best_coding = reg.resolve_best_model(capability="CODING")
    assert best_coding is not None
    assert "CODING" in [c.upper() for c in best_coding.capabilities]


def test_resolve_best_model_prefer_local():
    reg = canonical_model_registry
    best_local = reg.resolve_best_model(capability="LOCAL", prefer_local=True)
    assert best_local is not None
    assert best_local.source == ModelSource.LOCAL
    assert best_local.cost_class == CostClass.LOCAL


def test_duplicate_registration_raises():
    reg = CanonicalModelRegistry()
    duplicate_record = CanonicalModelRecord(
        model_id="local/qwen3:8b",
        source=ModelSource.LOCAL,
        raw_model_name="qwen3:8b",
        capabilities=["TEXT"],
        context_window=4096,
        cost_class=CostClass.LOCAL,
        latency_tier=LatencyTier.FAST,
        qualification_status=ModelQualificationStatus.QUALIFIED,
    )
    with pytest.raises(ValueError, match="Doublon détecté"):
        reg._register(duplicate_record)
