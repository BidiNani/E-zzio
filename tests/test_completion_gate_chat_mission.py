"""#4 — CompletionGate sur les chemins CHAT et MISSION.

Tout achèvement CHAT/MISSION doit passer par l'autorité canonique unique de
preuve (`CompletionGate.evaluate`) : un résultat worker ne s'auto-déclare
jamais PROVEN. CHAT sans évidence -> MEASURED (accepté, non bloquant) ;
MISSION avec sous-tâches OK -> PROVEN ; DAG incomplet -> REJECTED.
"""
from __future__ import annotations

import pytest

from core.ezzio_master import EzzioMaster
from core.providers.base_provider import CostClass, ProviderResponse


class FakeChatProvider:
    async def generate(self, prompt: str = "", model: str = "gemini-3.8-flash", **kwargs) -> ProviderResponse:
        return ProviderResponse(content=f"Fake response for: {prompt[:30]}", model=model,
                                provider="fake_provider", cost_class=CostClass.LOCAL)


class InMemoryGateway:
    def __init__(self):
        self.sessions = {}

    async def init(self):
        pass

    async def record_message(self, session_id: str, role: str, content: str, metadata=None):
        self.sessions.setdefault(session_id, []).append({"role": role, "content": content})

    async def get_session_history(self, session_id: str, limit: int = 10):
        return self.sessions.get(session_id, [])[-limit:]


class FakeDelegationProvider:
    async def generate(self, prompt: str = "", model: str = "gemini-3.8-flash", **kwargs) -> ProviderResponse:
        if "Synthèse Master" in prompt:
            content = f"[Synthèse E-ZZIO Master {model}] Mission orchestrée avec succès."
        else:
            content = f"[Résultat {model}] Audit/Code validé avec succès."
        return ProviderResponse(content=content, model=model,
                                provider="fake_provider", cost_class=CostClass.LOCAL)


@pytest.mark.asyncio
async def test_chat_completion_is_measured_not_proven():
    master = EzzioMaster(provider=FakeChatProvider())
    master.memory = InMemoryGateway()
    master._memory_initialized = True
    res = await master.execute_intent(user_prompt="Quelle est la capitale de la France ?",
                                      session_id="gate-chat-001", channel="web")
    assert res["ok"] is True
    # Pas d'artefact de preuve sur CHAT -> MEASURED, jamais PROVEN auto-déclaré.
    assert res["proof_status"] == "MEASURED"


@pytest.mark.asyncio
async def test_mission_success_is_proven():
    master = EzzioMaster(provider=FakeDelegationProvider())
    res = await master.orchestrate_multi_agent_mission(
        mission_prompt="Mission d'analyse de sécurité et correctif du module vault",
        subtask_specs=[
            {"task_id": "sub-01", "role": "forensic", "prompt": "Audit des vulnérabilités vault", "complexity": 0.6},
            {"task_id": "sub-02", "role": "coding", "prompt": "Correctif de code vault", "complexity": 0.7},
        ],
        session_id="gate-mission-ok", channel="web")
    assert res["ok"] is True
    assert res["proof_status"] == "PROVEN"


@pytest.mark.asyncio
async def test_mission_failure_is_rejected():
    master = EzzioMaster(provider=FakeDelegationProvider())
    res = await master.orchestrate_multi_agent_mission(
        mission_prompt="Mission avec sous-tâche refusée au budget",
        subtask_specs=[
            {"task_id": "sub-01", "role": "forensic", "prompt": "Audit vault", "complexity": 0.6},
            {"task_id": "sub-02", "role": "coding", "prompt": "Correctif vault", "complexity": 0.7,
             "budget_deny": True},
        ],
        session_id="gate-mission-ko", channel="web")
    # DAG incomplet -> le gate refuse la preuve ; le statut reflète l'échec.
    assert res["proof_status"] == "REJECTED"
    assert res["ok"] is False
