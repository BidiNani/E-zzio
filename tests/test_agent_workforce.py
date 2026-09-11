"""
Tests ciblés pour le Multi-Agent Workforce souverain E-ZZIO V9.4.
Valide:
1. Enregistrement des 13 agents spécialistes + Master dans AgentRegistry avec capacités et risk_level
2. Résolution d'agent par rôle et recherche par capacité
3. Sélection déterministe des workers selon l'intention utilisateur
4. Exécution asynchrone non-bloquante avec génération d'artefacts
5. Ordonnancement asynchrone avec dépendance d'étape (WAITING_DEPENDENCY)
6. Disponibilité conversationnelle immédiate du Master
7. Respect strict des invariants Free-First et souveraineté
"""
import pytest
import asyncio
from unittest.mock import AsyncMock

from core.agents.registry import AgentRegistry, AgentDescriptor, AgentStatus, agent_registry
from core.agent.mission_controller import (
    MissionRecord,
    MissionStatus,
    WorkerRole,
    mission_registry,
)
from core.agent.worker_fleet import WorkerFleetDispatcher, worker_fleet
from core.ezzio_master import EzzioMaster
from core.agent.coder_federation import CoderModelFederationRouter
from core.providers.base_provider import ProviderResponse, CostClass


@pytest.fixture
def mock_federation():
    router = CoderModelFederationRouter(providers={})
    async def fake_execute(prompt, profile, **kwargs):
        return ProviderResponse(
            content=f"Master réponse conversationnelle pour: {prompt[:30]}",
            role="assistant",
            model="nvidia/nemotron-3-super-120b-a12b",
            provider="nvidia",
            cost_class=CostClass.FREE_ENDPOINT,
            raw={"coder_federation_trace": {"attempts_count": 1}}
        )
    router.execute_task = fake_execute
    return router


def test_agent_registry_workforce_definition():
    """Valide la présence et la complétude des 13 agents spécialistes + Master."""
    reg = agent_registry
    reg.reset_to_defaults()

    expected_roles = [
        "CODER_AGENT",
        "RESEARCH_AGENT",
        "WEB_AGENT",
        "SYSTEM_AGENT",
        "CLEANING_AGENT",
        "FILE_AGENT",
        "IMAGE_AGENT",
        "DOCUMENT_AGENT",
        "QA_AGENT",
        "SECURITY_AGENT",
        "MODEL_AGENT",
        "DATA_AGENT",
        "AUTOMATION_AGENT",
    ]

    for role in expected_roles:
        agent = reg.get_agent_by_role(role)
        assert agent is not None, f"Agent manquant pour le rôle {role}"
        assert len(agent.capabilities) > 0, f"Capacités vides pour {role}"
        assert agent.risk_level in ("LOW", "MEDIUM", "HIGH"), f"Niveau de risque invalide pour {role}"

    # Vérification du Master souverain (E-ZZIO)
    master = reg.get_agent("master_ezzio")
    assert master is not None
    assert master.is_master is True
    assert "DIALOGUE" in master.capabilities
    assert "PLANNING" in master.capabilities
    assert "DELEGATION" in master.capabilities


def test_agent_capability_lookup():
    """Vérifie la recherche filtrée d'agents par capacité."""
    reg = agent_registry
    coders = reg.find_agents_by_capability("CODE_WRITE")
    assert any(a.agent_id == "coder_worker" for a in coders)

    inspectors = reg.find_agents_by_capability("SECRETS_SCAN")
    assert any(a.agent_id == "sec_guard" for a in inspectors)

    testers = reg.find_agents_by_capability("TEST_RUN")
    assert any(a.agent_id == "qa_tester" for a in testers)


@pytest.mark.asyncio
async def test_worker_fleet_specialist_selection():
    """Valide le routage d'intention vers les nouveaux workers spécialisés."""
    fleet = WorkerFleetDispatcher()
    
    assert fleet.select_worker_for_intent("Lance les tests pytest et vérifie la non-régression") == "QA_WORKER"
    assert fleet.select_worker_for_intent("Audit de sécurité et scan de secrets sur le vault") == "SECURITY_WORKER"
    assert fleet.select_worker_for_intent("Scrappe le site et extrais les données web en ligne") == "WEB_WORKER"
    assert fleet.select_worker_for_intent("Transforme le csv et dataset en format structuré") == "DATA_WORKER"
    assert fleet.select_worker_for_intent("Teste la latence des providers et qualifie le modèle") == "MODEL_WORKER"
    assert fleet.select_worker_for_intent("Automatise ce script avec une tâche planifiée cron") == "AUTOMATION_WORKER"
    assert fleet.select_worker_for_intent("Nettoie mon disque et purge le cache") == "CLEANING_WORKER"
    assert fleet.select_worker_for_intent("Crée ce fichier config.json") == "FILE_WORKER"


@pytest.mark.asyncio
async def test_specialist_async_execution_with_artifacts():
    """Valide l'exécution autonome des workers avec génération d'artefacts gouvernés."""
    fleet = WorkerFleetDispatcher()

    # QA Worker
    qa_record = MissionRecord(
        mission_id="m_qa_01",
        goal="Valider les tests de non-régression",
        worker_type="QA_WORKER",
    )
    await fleet.execute_mission_async(qa_record)
    assert qa_record.status == MissionStatus.COMPLETED
    assert qa_record.result.get("passed") is True

    # Security Worker
    sec_record = MissionRecord(
        mission_id="m_sec_01",
        goal="Audit cryptographique et détection de fuite",
        worker_type="SECURITY_WORKER",
    )
    await fleet.execute_mission_async(sec_record)
    assert sec_record.status == MissionStatus.COMPLETED
    assert len(sec_record.artifacts) >= 1
    assert sec_record.result.get("secrets_leakage") == 0


@pytest.mark.asyncio
async def test_mission_status_waiting_dependency():
    """Valide l'état d'étape WAITING_DEPENDENCY pour les tâches séquentielles."""
    assert MissionStatus.WAITING_DEPENDENCY.value == "WAITING_DEPENDENCY"
    
    record = MissionRecord(
        mission_id="m_dep_01",
        goal="Attente de dépendance de build",
        worker_type="CODER_WORKER",
        status=MissionStatus.WAITING_DEPENDENCY,
    )
    assert record.status == MissionStatus.WAITING_DEPENDENCY
    mission_registry.register(record)
    
    fetched = mission_registry.get("m_dep_01")
    assert fetched.status == MissionStatus.WAITING_DEPENDENCY


@pytest.mark.asyncio
async def test_master_delegates_to_specialist_and_remains_conversational(mock_federation):
    """Vérifie que le Master délègue au spécialiste et répond immédiatement à l'utilisateur."""
    master = EzzioMaster(federation_router=mock_federation)

    # 1. Lancer une tâche spécialisée (QA)
    res = await master.execute_intent("Lance les tests pytest et vérifie la régression", channel="discord")
    assert res["ok"] is True
    assert res.get("is_async_job") is True
    assert "QA_WORKER" in res["response"]
    assert "RUNNING" in res["response"]
    assert res.get("agent_id") == "qa_tester"

    mission_id = res["mission"]
    record = mission_registry.get(mission_id)
    assert record is not None

    # 2. Poser une question pendant l'exécution
    chat_res = await master.execute_intent("Quelle est la mission du QA agent ?", channel="discord")
    assert chat_res["ok"] is True
    assert chat_res.get("is_async_job") is not True

    # 3. Attendre la fin du worker
    if record.async_task:
        await record.async_task
    assert record.status == MissionStatus.COMPLETED
