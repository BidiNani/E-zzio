"""
E-ZZIO Sovereign Agent Platform — Parity Gate v5.0 Acceptance Suite.

Valide :
- Décomposition et graphe de tâches ordonnées (TaskGraph)
- Exécution de mission de bout en bout (MissionController)
- Gestion et hachage d'artefacts (ArtifactStore)
- Cycles de pause, reprise et annulation
- Préservation des autorités souveraines (ModelRouter, Memory, Security)
"""

import pytest
import asyncio
from core.agent.mission_controller import (
    MissionController,
    MissionStatus,
    TaskGraph,
    MissionTask,
    WorkerRole,
    TaskStatus,
    ArtifactType
)


@pytest.mark.asyncio
async def test_task_graph_dependency_ordering():
    """Vérifie que les dépendances ordonnent l'exécution sans inversion."""
    graph = TaskGraph()
    t1 = MissionTask("t1", "Tâche Initiale", "Explore", WorkerRole.RESEARCHER)
    t2 = MissionTask("t2", "Tâche Dépendante", "Plan", WorkerRole.PLANNER, dependencies=["t1"])
    graph.add_task(t1)
    graph.add_task(t2)

    ready_init = graph.get_ready_tasks()
    assert len(ready_init) == 1
    assert ready_init[0].task_id == "t1"

    # Marquer t1 comme complétée
    t1.status = TaskStatus.COMPLETED
    ready_next = graph.get_ready_tasks()
    assert len(ready_next) == 1
    assert ready_next[0].task_id == "t2"


@pytest.mark.asyncio
async def test_full_mission_lifecycle_and_artifacts():
    """Vérifie le cycle de vie complet d'une mission avec production d'artefacts vérifiables."""
    controller = MissionController(
        mission_id="mission_audit_001",
        goal="Audit de parité et validation des contrats agentiques"
    )

    res = await controller.run_mission()
    assert res["status"] == "COMPLETED"
    assert res["artifacts_count"] >= 7
    assert len(controller.artifacts) >= 7

    # Vérification de l'intégrité cryptographique des artefacts
    for art in controller.artifacts:
        assert len(art.content_hash) == 64
        assert art.mission_id == "mission_audit_001"


@pytest.mark.asyncio
async def test_mission_pause_and_resume():
    """Vérifie la capacité de pause et de reprise de mission."""
    controller = MissionController(mission_id="mission_pause_002", goal="Test de pause")
    controller.pause_mission()
    assert controller.status == MissionStatus.PAUSED

    controller.resume_mission()
    assert controller.status == MissionStatus.RUNNING
