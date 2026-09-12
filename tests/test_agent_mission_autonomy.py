"""Tests unitaires déterministes pour l'autonomie réelle des missions agentiques dans EzzioMaster."""

import pytest
import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock
from core.ezzio_master import EzzioMaster
from core.providers.base_provider import CostClass, ProviderResponse


class FakeMissionProvider:
    """Provider fake déterministe enregistrant les prompts pour valider l'injection d'actions réelles."""

    def __init__(self):
        self.calls = []

    async def generate(
        self,
        prompt: str = "",
        system_prompt: str = None,
        model: str = "gemini-3.8-flash",
        temperature: float = 0.2,
        max_tokens: int = 512,
        thinking_level: str = "off",
        **kwargs
    ) -> ProviderResponse:
        self.calls.append({
            "prompt": prompt,
            "system_prompt": system_prompt,
            "model": model,
            "thinking_level": thinking_level,
        })
        return ProviderResponse(
            content=f"[Fake LLM Response for: {prompt[:40]}]",
            model=model,
            provider="fake_mission_provider",
            cost_class=CostClass.LOCAL,
        )


@pytest.mark.asyncio
async def test_mission_with_real_action_file_inspection():
    """1. Mission simple avec action réelle d'inspection de fichier local."""
    fake_prov = FakeMissionProvider()
    master = EzzioMaster(provider=fake_prov)

    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt", dir="G:/AI/E-zzio/runtime") as tmp:
        tmp.write("CONFIDENTIAL_TEST_DATA: key=SECURE_987654321")
        tmp_path = tmp.name

    try:
        subtasks = [
            {
                "task_id": "subtask-file-inspect-01",
                "role": "RESEARCH",
                "prompt": "Inspecter le fichier de test pour extraire la clé",
                "target": tmp_path,
                "complexity": 0.5
            }
        ]

        t0 = time.perf_counter()
        res = await master.orchestrate_multi_agent_mission(
            mission_prompt="Inspecter le fichier local et synthétiser",
            subtask_specs=subtasks
        )
        elapsed_ms = int((time.perf_counter() - t0) * 1000)

        assert res["ok"] is True
        assert len(res["subtasks"]) == 1
        st = res["subtasks"][0]

        # Verification de l'action reelle
        assert st["preflight_ready"] is True
        assert st["action_executed"] is True
        assert st["action_status"] == "READY"
        assert st["action_valid"] is True

        # Le prompt recu par le provider de la sous-tache DOIT contenir les donnees reelles
        subtask_call = fake_prov.calls[0]
        assert "CONFIDENTIAL_TEST_DATA" in subtask_call["prompt"]
        assert "SECURE_987654321" in subtask_call["prompt"]

        # Synthèse Master
        assert res["synthesis"] is not None
        assert len(fake_prov.calls) == 2  # 1 subtask + 1 synthesis master

    finally:
        Path(tmp_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_multi_agent_mission_two_subtasks_with_preflight_and_audit():
    """2 & 3 & 4 & 5 & 6. Mission multi-agent avec 2 sous-tâches, preflight, transmission résultat au Master, validation et audit."""
    fake_prov = FakeMissionProvider()
    master = EzzioMaster(provider=fake_prov)

    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".log", dir="G:/AI/E-zzio/runtime") as tmp:
        tmp.write("LOG_ENTRY 2026-09-12 14:00:00 ERROR_CODE_500 Database timeout")
        tmp_path = tmp.name

    try:
        subtasks = [
            {
                "task_id": "subtask-audit-01",
                "role": "FORENSIC",
                "prompt": "Auditer les logs d'erreur",
                "target": tmp_path,
                "complexity": 0.6
            },
            {
                "task_id": "subtask-fix-02",
                "role": "CODING",
                "prompt": "Proposer un patch d'optimisation",
                "complexity": 0.7
            }
        ]

        res = await master.orchestrate_multi_agent_mission(
            mission_prompt="Mission d'analyse d'incidents et correctif",
            subtask_specs=subtasks
        )

        assert res["ok"] is True
        assert len(res["subtasks"]) == 2

        st1, st2 = res["subtasks"]

        # Preflight et actions
        assert st1["preflight_ready"] is True
        assert st1["action_executed"] is True
        assert st1["action_status"] == "READY"

        assert st2["preflight_ready"] is True
        assert st2["action_executed"] is False
        assert st2["action_status"] == "N/A"

        # Verification que le Master a recu les statuts d'action dans son prompt de synthese
        master_call = fake_prov.calls[2]  # Call 0 = subtask 1, Call 1 = subtask 2, Call 2 = Master Synthesis
        assert "(Action: READY)" in master_call["prompt"]

    finally:
        Path(tmp_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_controlled_tool_failure_non_existent_target():
    """7. Échec contrôlé d'un outil : cible inexistante gérée proprement sans crash."""
    fake_prov = FakeMissionProvider()
    master = EzzioMaster(provider=fake_prov)

    subtasks = [
        {
            "task_id": "subtask-missing-file-01",
            "role": "RESEARCH",
            "prompt": "Tenter de lire un fichier incalculable",
            "target": "G:/AI/E-zzio/runtime/non_existent_file_9999.txt",
            "complexity": 0.5
        }
    ]

    res = await master.orchestrate_multi_agent_mission(
        mission_prompt="Mission avec ressource manquante",
        subtask_specs=subtasks
    )

    assert res["ok"] is True
    st = res["subtasks"][0]
    assert st["action_executed"] is True
    assert st["action_status"] in ["UNAVAILABLE", "ERROR"]
    assert st["action_valid"] is False


@pytest.mark.asyncio
async def test_unauthorized_action_prevention():
    """8. Aucune action non autorisée (protection contre la traversée de répertoire hors workspace)."""
    fake_prov = FakeMissionProvider()
    master = EzzioMaster(provider=fake_prov)

    # Tentative d'accès à un fichier hors périmètre workspace E-ZZIO
    subtasks = [
        {
            "task_id": "subtask-traversal-01",
            "role": "RESEARCH",
            "prompt": "Tenter d'accéder au fichier Windows SAM",
            "target": "C:/Windows/System32/drivers/etc/hosts",
            "complexity": 0.5
        }
    ]

    res = await master.orchestrate_multi_agent_mission(
        mission_prompt="Mission avec tentative hors périmètre",
        subtask_specs=subtasks
    )

    assert res["ok"] is True
    st = res["subtasks"][0]
    # InputAccessManager bloque les chemins hors G:\AI\E-zzio
    assert st["action_status"] == "BLOCKED"
    assert st["action_valid"] is False
