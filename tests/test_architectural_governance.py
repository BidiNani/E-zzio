"""tests/test_architectural_governance.py — Tests constitutionnels de routage et gouvernance E-ZZIO."""
import ast
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from core.agent.coder_federation import (
    CoderModelFederationRouter,
    PrivacyRequirement,
    TaskProfile,
    TaskType,
)
from core.routing.model_registry import canonical_model_registry


def test_a_all_business_models_in_canonical_registry():
    """TEST A: Aucun modèle métier ne doit être sélectionné hors du CanonicalModelRegistry."""
    router = CoderModelFederationRouter()

    for task_type in TaskType:
        for privacy in PrivacyRequirement:
            profile = TaskProfile(task_type=task_type, privacy=privacy)
            plan = router.resolve_candidates(profile)
            assert plan.primary is not None
            model_name = plan.primary.model_name
            rec = canonical_model_registry.get(model_name)
            assert rec is not None, f"Le modèle {model_name} n'est pas enregistré dans CanonicalModelRegistry"


def test_b_no_direct_provider_instantiation():
    """TEST B: Aucun provider ne doit être instancié directement (ast.Call) dans ezzio_master, agent, cognition,

    hors des façades legacy / registres autorisés.
    """
    root_dir = Path(r"G:\AI\E-zzio")
    targets = [
        root_dir / "core" / "ezzio_master.py",
        root_dir / "core" / "agent",
        root_dir / "core" / "cognition",
    ]

    allowed_files = {
        "agent_provider.py",  # Façade legacy
    }

    forbidden_classes = {
        "GeminiProvider",
        "GroqProvider",
        "OllamaProvider",
        "OpenRouterProvider",
        "NvidiaNimProvider",
    }

    violations = []

    def check_file(p: Path):
        if p.name in allowed_files:
            return
        content = p.read_text(encoding="utf-8")
        try:
            tree = ast.parse(content, filename=p.name)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func = node.func
                    func_name = None
                    if isinstance(func, ast.Name):
                        func_name = func.id
                    elif isinstance(func, ast.Attribute):
                        func_name = func.attr
                    if func_name in forbidden_classes:
                        violations.append(f"{p.name}:{node.lineno}: instanciation directe de {func_name}()")
        except SyntaxError:
            pass

    for target in targets:
        if target.is_file():
            check_file(target)
        elif target.is_dir():
            for p in target.glob("*.py"):
                check_file(p)

    assert not violations, f"Instanciations directes interdites de provider : {violations}"


def test_c_resolve_candidates_respects_task_profile():
    """TEST C: coder_federation.resolve_candidates() doit réellement respecter TaskProfile."""
    router = CoderModelFederationRouter()

    # CODING cloud
    p_coding = TaskProfile(task_type=TaskType.CODING, privacy=PrivacyRequirement.ALLOW_CLOUD)
    plan_coding = router.resolve_candidates(p_coding)
    assert plan_coding.primary is not None
    assert plan_coding.primary.provider_name == "gemini"
    assert "CODING" in plan_coding.primary.capabilities

    # CODING local_only
    p_local = TaskProfile(task_type=TaskType.CODING, privacy=PrivacyRequirement.LOCAL_ONLY)
    plan_local = router.resolve_candidates(p_local)
    assert plan_local.primary is not None
    assert plan_local.primary.is_local is True
    assert plan_local.primary.provider_name == "ollama"

    # REASONING
    p_reasoning = TaskProfile(task_type=TaskType.REASONING, privacy=PrivacyRequirement.ALLOW_CLOUD)
    plan_reasoning = router.resolve_candidates(p_reasoning)
    assert plan_reasoning.primary is not None
    assert "REASONING" in plan_reasoning.primary.capabilities or plan_reasoning.primary.model_name == "deepseek-r1:7b"


@pytest.mark.asyncio
async def test_d_master_fallback_uses_provider_factory(monkeypatch):
    """TEST D: Le fallback du Master doit utiliser ProviderFactory."""
    from core.ezzio_master import EzzioMaster
    from core.providers.base_provider import ProviderResponse
    from core.providers.registry import ProviderFactory

    master = EzzioMaster()

    factory_calls = []

    def mock_create(name: str, **kwargs):
        factory_calls.append(name)
        fake_prov = AsyncMock()
        fake_prov.generate = AsyncMock(return_value=ProviderResponse(
            content="Fallback content ok",
            model="gemini-3.5-flash-lite",
            provider="gemini",
        ))
        return fake_prov

    monkeypatch.setattr(ProviderFactory, "create", mock_create)

    resp, notice = await master._try_fallback(
        detected_provider="groq",
        original_model="llama-3.3-70b-versatile",
        reason="test_error",
        user_prompt="test prompt",
        chat_system="sys prompt",
        thinking_level="off",
    )

    assert resp is not None
    assert notice is not None
    assert len(factory_calls) > 0, "ProviderFactory.create() n'a pas été appelé par _try_fallback !"
