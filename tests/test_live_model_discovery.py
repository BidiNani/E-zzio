import pytest

from core.cognition.execution_decision_engine import ExecutionDecisionEngine
from core.routing.lifecycle import (
    LiveModelRecord,
    ModelCatalogDiscoveryEngine,
    ModelLifecycleStatus,
)


def test_model_lifecycle_status_enum():
    assert ModelLifecycleStatus.AVAILABLE.value == "AVAILABLE"
    assert ModelLifecycleStatus.RETIRED.value == "RETIRED"
    assert ModelLifecycleStatus.ACCESS_DENIED.value == "ACCESS_DENIED"
    assert ModelLifecycleStatus.UNREACHABLE.value == "UNREACHABLE"
    assert ModelLifecycleStatus.STALE.value == "STALE"


def test_catalog_discovery_engine_diff():
    engine = ModelCatalogDiscoveryEngine()

    # Initial snapshot
    initial_records = [
        LiveModelRecord("groq", "llama-3.3-70b", status=ModelLifecycleStatus.AVAILABLE, eligible=True),
        LiveModelRecord("groq", "old-model-v1", status=ModelLifecycleStatus.AVAILABLE, eligible=True),
    ]
    engine.update_catalog(initial_records, provider_statuses={"groq": "healthy"})

    assert engine.is_model_eligible("groq", "llama-3.3-70b") is True

    # New snapshot: old-model-v1 removed, new-model-v2 added
    new_snapshot = [
        LiveModelRecord("groq", "llama-3.3-70b", status=ModelLifecycleStatus.AVAILABLE, eligible=True),
        LiveModelRecord("groq", "new-model-v2", status=ModelLifecycleStatus.AVAILABLE, eligible=True),
    ]

    diff = engine.update_catalog(new_snapshot, provider_statuses={"groq": "healthy"})

    assert len(diff.new_models) == 1
    assert diff.new_models[0].model_id == "new-model-v2"

    assert len(diff.removed_models) == 1
    assert diff.removed_models[0].model_id == "old-model-v1"
    assert diff.removed_models[0].status == ModelLifecycleStatus.RETIRED

    assert engine.is_model_eligible("groq", "old-model-v1") is False


def test_catalog_discovery_provider_unreachable_does_not_retire():
    engine = ModelCatalogDiscoveryEngine()

    initial_records = [
        LiveModelRecord("gemini", "gemini-3.5-flash", status=ModelLifecycleStatus.AVAILABLE, eligible=True),
    ]
    engine.update_catalog(initial_records, provider_statuses={"gemini": "healthy"})

    # Provider becomes unreachable (empty list, provider status = unreachable)
    diff = engine.update_catalog([], provider_statuses={"gemini": "unreachable"})

    # Removed list should be empty because provider is unreachable, not healthy
    assert len(diff.removed_models) == 0
    # Status should remain unchanged or stale, not RETIRED
    assert engine.get_model_status("gemini", "gemini-3.5-flash") == ModelLifecycleStatus.AVAILABLE


def test_execution_decision_engine_rejects_retired_models(tmp_path):
    engine = ExecutionDecisionEngine(workspace_root=str(tmp_path))

    # Register model as RETIRED in catalog discovery
    from core.routing.lifecycle import model_catalog_discovery
    model_catalog_discovery.register_model_state(
        provider_id="groq",
        model_id="gemini-3.5-flash-lite",  # Default model returned by router in mock
        status=ModelLifecycleStatus.RETIRED,
        eligible=False,
    )

    decision = engine.evaluate_and_decide(
        task_type="coding",
        require_worker=False,
    )

    # Should fallback to Native Worker or an eligible target
    if decision.execution_type == "MODEL":
        assert decision.target_id != "gemini-3.5-flash-lite"
    else:
        assert decision.execution_type == "WORKER"
        assert decision.target_id in ("native", "hermes", "cline", "pig")
