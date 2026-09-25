"""
tests/test_mission_agent_runtime.py — Tests de conformité souveraine pour le Runtime de Mission & Agents.

Vérifie l'intégralité du cycle canonique :
Mission -> Décomposition -> Sélection Agent -> Exécution Outil -> Validation & Retry -> Synthèse Master -> Discord
"""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from core.agent.mission_controller import MissionStatus, mission_registry
from core.agents.registry import AgentStatus, agent_registry
from core.ezzio_master import EzzioMaster
from core.providers.base_provider import CostClass, ProviderResponse


class FakeMissionProvider:
    """Provider fake déterministe pour tests sans appel réseau externe."""

    def __init__(self):
        self.calls = []

    async def generate(
        self,
        prompt: str = "",
        system_prompt: str | None = None,
        model: str = "gemini-3.8-flash",
        temperature: float = 0.2,
        max_tokens: int = 512,
        thinking_level: str = "off",
        **kwargs
    ) -> ProviderResponse:
        self.calls.append({
            "prompt": prompt,
            "model": model,
            "thinking_level": thinking_level,
        })
        if "Synthèse Master" in prompt:
            content = f"[SYNTHÈSE CERTIFIÉE E-ZZIO {model}] Mission accomplie avec succès. Tous les objectifs sont validés."
        else:
            content = f"[RÉSULTAT AGENT {model}] Analyse technique et exécution validées sans anomalie."

        return ProviderResponse(
            content=content,
            model=model,
            provider="fake_provider",
            cost_class=CostClass.LOCAL,
        )


@pytest.mark.asyncio
async def test_mission_decomposition_and_planning():
    """Vérifie que le Master décompose automatiquement une mission sans spécifications préalables."""
    fake_prov = FakeMissionProvider()
    master = EzzioMaster(provider=fake_prov)

    # Mission avec mot-clé de validation/test
    prompt = "Inspecte le module vault et vérifie les tests de non-régression"
    res = await master.orchestrate_multi_agent_mission(
        mission_prompt=prompt,
        session_id="session-decomp-01",
        channel="web"
    )

    assert res["ok"] is True
    assert len(res["subtasks"]) >= 2
    roles = [s["role"] for s in res["subtasks"]]
    assert "forensic" in roles
    assert "coding" in roles or "qa" in roles
    assert res["master_model"] == "gemini-3.8-flash"
    assert "SYNTHÈSE CERTIFIÉE" in res["synthesis"]


@pytest.mark.asyncio
async def test_agent_registry_lifecycle():
    """Vérifie que l'agent assigné du registre d'agents passe par l'état BUSY puis revient à IDLE."""
    fake_prov = FakeMissionProvider()
    master = EzzioMaster(provider=fake_prov)

    coder = agent_registry.get_agent("coder_worker")
    assert coder is not None
    assert coder.status == AgentStatus.IDLE

    subtasks = [
        {
            "task_id": "subtask-code-verify",
            "role": "coding",
            "prompt": "Génère le patch pour le composant",
            "complexity": 0.7
        }
    ]

    res = await master.orchestrate_multi_agent_mission(
        mission_prompt="Mission code isolate",
        subtask_specs=subtasks,
        session_id="session-lifecycle-01"
    )

    assert res["ok"] is True
    # Vérification que le statut de l'agent est bien revenu à IDLE après exécution
    assert coder.status == AgentStatus.IDLE
    assert coder.current_task_id is None
    assert res["subtasks"][0]["agent_id"] == "coder_worker"


@pytest.mark.asyncio
async def test_subtask_tool_execution_governed():
    """Vérifie l'exécution réelle d'un outil (read_file) via ToolRegistry sous gouvernance PolicyGuard."""
    fake_prov = FakeMissionProvider()
    master = EzzioMaster(provider=fake_prov)

    subtasks = [
        {
            "task_id": "subtask-read-governed",
            "role": "research",
            "tool_name": "read_file",
            "tool_args": {"path": "conftest.py"},
            "prompt": "Analyse le fichier conftest.py",
            "complexity": 0.5
        }
    ]

    res = await master.orchestrate_multi_agent_mission(
        mission_prompt="Inspecte le conftest",
        subtask_specs=subtasks,
        session_id="session-tool-01"
    )

    assert res["ok"] is True
    sub = res["subtasks"][0]
    assert sub["tool"] == "read_file"
    assert sub["tool_result"] is not None
    assert len(sub["tool_result"]) > 0
    assert sub["validated"] is True
    assert sub["status"] == "SUCCESS"


@pytest.mark.asyncio
async def test_validation_and_retry_recovery():
    """Vérifie qu'un échec de validation déclenche la boucle de retry avec feedback correctif."""
    master = EzzioMaster()

    # Création d'un provider simulant un échec au tour 1 puis un succès au tour 2
    attempts = {"count": 0}

    class FlakyProvider:
        async def generate(self, prompt="", model="", **kwargs):
            attempts["count"] += 1
            if attempts["count"] == 1:
                # Échec au premier essai (contenu vide -> validation rejetée)
                return ProviderResponse(content="", model=model, provider="flaky", cost_class=CostClass.LOCAL)
            # Récupération au retry
            return ProviderResponse(
                content="[RECOVERED] Analyse complétée après correction.",
                model=model,
                provider="flaky",
                cost_class=CostClass.LOCAL
            )

    master._injected_provider = FlakyProvider()
    master.provider = master._injected_provider

    subtasks = [
        {
            "task_id": "subtask-flaky",
            "role": "forensic",
            "prompt": "Analyse critique des logs",
            "complexity": 0.6
        }
    ]

    res = await master.orchestrate_multi_agent_mission(
        mission_prompt="Mission avec retry",
        subtask_specs=subtasks,
        session_id="session-retry-01",
        max_retries=2
    )

    assert res["ok"] is True
    sub = res["subtasks"][0]
    assert sub["retries"] == 1
    assert sub["validated"] is True
    assert sub["status"] == "SUCCESS"
    assert "RECOVERED" in sub["output"]


@pytest.mark.asyncio
async def test_mission_registry_tracking():
    """Vérifie que la mission est enregistrée et tracée dans le MissionRegistry."""
    fake_prov = FakeMissionProvider()
    master = EzzioMaster(provider=fake_prov)

    res = await master.orchestrate_multi_agent_mission(
        mission_prompt="Audit global de conformité",
        session_id="session-tracking-01"
    )

    mission_id = res["mission_id"]
    record = mission_registry.get(mission_id)
    assert record is not None
    assert record.mission_id == mission_id
    assert record.status == MissionStatus.SUCCEEDED
    assert record.worker_type == "MULTI_AGENT"
    assert "master_model" in record.result


@pytest.mark.asyncio
async def test_master_execute_intent_mission_profile():
    """Vérifie que execute_intent(mission_profile='MISSION') active le runtime de mission complet."""
    fake_prov = FakeMissionProvider()
    master = EzzioMaster(provider=fake_prov)

    res = await master.execute_intent(
        user_prompt="Mission autonome : audite le système et synthétise",
        mission_profile="MISSION",
        session_id="session-intent-mission-01",
        channel="web"
    )

    assert res["ok"] is True
    assert res["mission"] == "MISSION"
    assert "mission_id" in res
    assert "subtasks" in res
    assert len(res["subtasks"]) >= 2
    assert "SYNTHÈSE CERTIFIÉE" in res["response"]


@pytest.mark.asyncio
async def test_discord_channel_mission_flow():
    """Vérifie le routage et le formatage unifié de mission pour le canal Discord."""
    fake_prov = FakeMissionProvider()
    master = EzzioMaster(provider=fake_prov)

    res = await master.execute_intent(
        user_prompt="!e --profile=MISSION analyse la base de données et valide les migrations",
        mission_profile="MISSION",
        session_id="discord-user-186035306418405376",
        channel="discord"
    )

    assert res["ok"] is True
    assert res["channel"] == "discord"
    assert res["mission"] == "MISSION"
    assert res["authority"] == "CanonicalIdentity"
    assert len(res["subtasks"]) >= 2
    # Doit contenir la synthèse exploitable par Discord
    assert res["response"] is not None
    assert len(res["response"]) > 0


@pytest.mark.asyncio
async def test_e2e_two_agent_tool_pipeline():
    """PREUVE E2E : Pipeline complet à deux agents avec outil, validation et synthèse Master.

    AGENT A (researcher_scout) : Inspecte le fichier pyproject.toml via read_file.
    AGENT B (qa_tester) : Valide la conformité de l'inspection.
    MASTER (master_ezzio) : Synthétise la décision finale.
    """
    fake_prov = FakeMissionProvider()
    master = EzzioMaster(provider=fake_prov)

    mission_goal = "Inspection architecturale de pyproject.toml et validation QA"

    subtasks = [
        {
            "task_id": "step-1-inspect",
            "role": "research",
            "tool_name": "read_file",
            "tool_args": {"path": "pyproject.toml"},
            "prompt": "Inspecte pyproject.toml et relève les dépendances principales",
            "complexity": 0.5
        },
        {
            "task_id": "step-2-validate",
            "role": "qa",
            "prompt": "Vérifie la conformité des dépendances inspectées",
            "complexity": 0.6
        }
    ]

    res = await master.orchestrate_multi_agent_mission(
        mission_prompt=mission_goal,
        subtask_specs=subtasks,
        session_id="session-e2e-proof-01",
        channel="discord"
    )

    # 1. Mission acceptée et réussie
    assert res["ok"] is True
    assert res["mission"] == mission_goal
    assert "mission_id" in res

    # 2. Agent A (researcher_scout) a utilisé l'outil read_file
    sub_a = res["subtasks"][0]
    assert sub_a["role"] == "research"
    assert sub_a["agent_id"] == "researcher_scout"
    assert sub_a["tool"] == "read_file"
    assert sub_a["tool_result"] is not None
    assert "project" in sub_a["tool_result"] or "pytest" in sub_a["tool_result"] or len(sub_a["tool_result"]) > 0
    assert sub_a["validated"] is True
    assert sub_a["status"] == "SUCCESS"

    # 3. Agent B (qa_tester) a validé
    sub_b = res["subtasks"][1]
    assert sub_b["role"] == "qa"
    assert sub_b["agent_id"] == "qa_tester"
    assert sub_b["validated"] is True
    assert sub_b["status"] == "SUCCESS"

    # 4. Synthèse Master
    assert res["master_model"] == "gemini-3.8-flash"
    assert "SYNTHÈSE CERTIFIÉE" in res["synthesis"]

    # 5. Traçabilité dans mission_registry
    rec = mission_registry.get(res["mission_id"])
    assert rec is not None
    assert rec.status == MissionStatus.SUCCEEDED
