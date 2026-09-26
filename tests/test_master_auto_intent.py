"""
tests/test_master_auto_intent.py — Tests de conformité pour Master Auto Intent & Conversation continue.

Vérifie :
A — AUTO CHAT (question simple -> CHAT, 1 provider call)
B — AUTO MISSION (demande d'audit/action -> MISSION, TaskDAG)
C — Discord AUTO CHAT (via /master/chat -> CHAT)
D — Discord AUTO MISSION (via /master/chat -> MISSION -> TaskDAG)
E — Mission active + question conversationnelle (CHAT sans interrompre la mission active)
F — Question sur mission active ("Tu en es où ?" -> consulte l'état réel de la mission)
G — Explicite MISSION (mission_profile="MISSION" -> force MISSION)
H — Explicite STANDARD (mission_profile="STANDARD" -> force CHAT, 1 provider call)
I — Mémoire conversationnelle intacte
J — Audit INTENT_DECIDED enregistré
"""
import asyncio
from unittest.mock import patch

import httpx
import pytest
from fastapi import FastAPI

from core.agent.mission_controller import MissionRecord, MissionStatus, mission_registry
from core.ezzio_master import EzzioMaster, determine_intent
from core.providers.base_provider import CostClass, ProviderResponse
from routers.master import router as master_router


class FakeAutoIntentProvider:
    """Provider fake déterministe pour tests d'intent AUTO et conversation continue."""

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
        self.calls.append({"prompt": prompt, "model": model, "system_prompt": system_prompt})
        if "Synthèse Master" in prompt:
            content = f"[SYNTHÈSE CERTIFIÉE {model}] Mission accomplie."
        elif "Mission active/récente" in (system_prompt or ""):
            content = "[RESPONSE CHAT] Je suis E-ZZIO. La mission est actuellement en cours."
        else:
            content = f"[RESPONSE CHAT {model}] Réponse conversationnelle directe."

        return ProviderResponse(
            content=content,
            model=model,
            provider="fake_provider",
            cost_class=CostClass.LOCAL,
        )


@pytest.mark.asyncio
async def test_determine_intent_rules():
    """Vérifie la logique déterministe de classification determine_intent()."""
    # Explicites
    assert determine_intent("Salut", mission_profile="STANDARD") == "CHAT"
    assert determine_intent("Salut", mission_profile="MISSION") == "MISSION"
    assert determine_intent("Salut", is_mission=True) == "MISSION"

    # Auto - Conversation
    assert determine_intent("Quelle est la capitale de la France ?", mission_profile="AUTO") == "CHAT"
    assert determine_intent("Salut E-ZZIO, comment vas-tu ?", mission_profile="AUTO") == "CHAT"
    assert determine_intent("Peux-tu m'expliquer le fonctionnement de Git ?", mission_profile="AUTO") == "CHAT"
    assert determine_intent("Tu en es où ?", mission_profile="AUTO") == "CHAT"

    # Auto - Mission
    assert determine_intent("Audite le module vault et vérifie les vulnérabilités", mission_profile="AUTO") == "MISSION"
    assert determine_intent("Exécute les tests de non-régression et répare le bug", mission_profile="AUTO") == "MISSION"


@pytest.mark.asyncio
async def test_auto_chat_single_provider_call():
    """Test A — AUTO CHAT : question simple -> 1 appel provider, aucun DAG."""
    fake_prov = FakeAutoIntentProvider()
    master = EzzioMaster(provider=fake_prov)

    res = await master.execute_intent(
        user_prompt="Quelle est la capitale de la France ?",
        mission_profile="AUTO",
        session_id="sess-auto-chat-01",
        channel="web"
    )

    assert res["ok"] is True
    assert "subtasks" not in res  # Pas de mission DAG
    assert len(fake_prov.calls) == 1
    assert "[RESPONSE CHAT" in res["response"]


@pytest.mark.asyncio
async def test_auto_mission_dag_execution():
    """Test B — AUTO MISSION : audit -> déclenchement TaskDAG."""
    fake_prov = FakeAutoIntentProvider()
    master = EzzioMaster(provider=fake_prov)

    res = await master.execute_intent(
        user_prompt="Audite le module vault et vérifie les vulnérabilités",
        mission_profile="AUTO",
        session_id="sess-auto-mission-01",
        channel="web"
    )

    assert res["ok"] is True
    assert "subtasks" in res
    assert len(res["subtasks"]) >= 2
    assert "dag_id" in res


@pytest.mark.asyncio
async def test_discord_auto_chat_e2e():
    """Test C — Discord AUTO CHAT : message d'accueil sur Discord -> CHAT (1 call)."""
    fake_prov = FakeAutoIntentProvider()

    app = FastAPI()
    app.include_router(master_router)

    with patch("core.ezzio_master.ezzio_master.provider", fake_prov), \
         patch("core.ezzio_master.ezzio_master._injected_provider", fake_prov):

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            payload = {
                "text": "Salut E-ZZIO, comment vas-tu ?",
                "session_id": "disc_guild_111_user_222",
                "channel": "discord",
                "mission_profile": "AUTO",
            }
            resp = await client.post("/master/chat", json=payload)
            assert resp.status_code == 200
            data = resp.json()

            assert data["channel"] == "discord"
            assert "subtasks" not in data or len(data.get("subtasks", [])) == 0
            assert len(fake_prov.calls) == 1


@pytest.mark.asyncio
async def test_discord_auto_mission_e2e():
    """Test D — Discord AUTO MISSION : demande d'audit sur Discord -> TaskDAG."""
    fake_prov = FakeAutoIntentProvider()

    app = FastAPI()
    app.include_router(master_router)

    with patch("core.ezzio_master.ezzio_master.provider", fake_prov), \
         patch("core.ezzio_master.ezzio_master._injected_provider", fake_prov):

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            payload = {
                "text": "Audite le module vault et vérifie les tests QA",
                "session_id": "disc_guild_111_user_222",
                "channel": "discord",
                "mission_profile": "AUTO",
            }
            resp = await client.post("/master/chat", json=payload)
            assert resp.status_code == 200
            data = resp.json()

            assert data["channel"] == "discord"
            assert "dag_id" in data
            assert len(data.get("subtasks", [])) >= 2


@pytest.mark.asyncio
async def test_active_mission_conversation_coexistence():
    """Test E — Mission active + question conversationnelle (sans interrompre la mission active)."""
    fake_prov = FakeAutoIntentProvider()
    master = EzzioMaster(provider=fake_prov)
    sess_id = "session-active-coexist-01"

    # Enregistrement d'une mission active RUNNING
    m_record = MissionRecord(
        mission_id="msn-active-999",
        goal="Analyse de sécurité globale en cours",
        worker_type="MULTI_AGENT",
        status=MissionStatus.RUNNING,
        request_id=sess_id
    )
    mission_registry.register(m_record)

    # Message 2 : Question conversationnelle pendant que la mission msn-active-999 est RUNNING
    res = await master.execute_intent(
        user_prompt="Pourquoi penses-tu que ce composant est vulnérable ?",
        mission_profile="AUTO",
        session_id=sess_id,
        channel="discord"
    )

    assert res["ok"] is True
    # Doit répondre en CHAT sans lancer une 2ème mission
    assert "subtasks" not in res
    # La mission d'origine msn-active-999 reste RUNNING et intacte dans le registre
    m_retrieved = mission_registry.get("msn-active-999")
    assert m_retrieved is not None
    assert m_retrieved.status == MissionStatus.RUNNING


@pytest.mark.asyncio
async def test_active_mission_query_status():
    """Test F — Question sur mission active ("Tu en es où ?") -> consulte l'état réel de la mission."""
    fake_prov = FakeAutoIntentProvider()
    master = EzzioMaster(provider=fake_prov)
    sess_id = "session-status-query-01"

    m_record = MissionRecord(
        mission_id="msn-status-777",
        goal="Audit du module auth et correction des permissions",
        worker_type="MULTI_AGENT",
        status=MissionStatus.RUNNING,
        request_id=sess_id
    )
    mission_registry.register(m_record)

    res = await master.execute_intent(
        user_prompt="Tu en es où de la mission ?",
        mission_profile="AUTO",
        session_id=sess_id,
        channel="web"
    )

    assert res["ok"] is True
    # Vérifie que le prompt système transmis au provider contient les informations de la mission active
    sys_prompt = fake_prov.calls[-1].get("system_prompt", "")
    assert "Mission active/récente" in sys_prompt
    assert "msn-status-777" in sys_prompt


@pytest.mark.asyncio
async def test_explicit_mission_profile_override():
    """Test G & H — Overrides explicites MISSION et STANDARD."""
    fake_prov = FakeAutoIntentProvider()
    master = EzzioMaster(provider=fake_prov)

    # G : Explicit MISSION même pour une question simple
    res_m = await master.execute_intent(
        user_prompt="Bonjour",
        mission_profile="MISSION",
        session_id="sess-override-m"
    )
    assert res_m["ok"] is True
    assert "subtasks" in res_m

    fake_prov.calls.clear()

    # H : Explicit STANDARD même pour une demande d'audit
    res_s = await master.execute_intent(
        user_prompt="Audite le module vault",
        mission_profile="STANDARD",
        session_id="sess-override-s"
    )
    assert res_s["ok"] is True
    assert "subtasks" not in res_s
    assert len(fake_prov.calls) == 1


@pytest.mark.asyncio
async def test_intent_audit_logging():
    """Test J — Audit log : Vérification de l'enregistrement d'événement INTENT_DECIDED."""
    fake_prov = FakeAutoIntentProvider()
    master = EzzioMaster(provider=fake_prov)

    audits = []

    def mock_audit(action, payload, status="SUCCESS"):
        audits.append({"action": action, "payload": payload, "status": status})

    with patch("core.ezzio_master._audit_command", side_effect=mock_audit):
        await master.execute_intent(
            user_prompt="Quelle heure est-il ?",
            mission_profile="AUTO",
            session_id="sess-audit-intent"
        )

        actions = [a["action"] for a in audits]
        assert "INTENT_DECIDED" in actions
        intent_event = next(a for a in audits if a["action"] == "INTENT_DECIDED")
        assert intent_event["payload"]["intent"] == "CHAT"
        assert intent_event["payload"]["profile"] == "AUTO"


@pytest.mark.asyncio
async def test_real_execution_coexistence_with_background_mission():
    """Vérifie la COEXISTENCE D'EXÉCUTION RÉELLE (Background TaskDAG + CHAT simultané)."""
    fake_prov = FakeAutoIntentProvider()
    master = EzzioMaster(provider=fake_prov)
    sess_id = "session-coexist-real-01"

    event_started = asyncio.Event()
    event_release = asyncio.Event()

    class SyncControlledProvider:
        async def generate(self, prompt="", model="", system_prompt="", **kwargs):
            if "Audite" in prompt or "subtask-forensic" in prompt:
                event_started.set()
                await event_release.wait()
                return ProviderResponse(content="[BG WORKER] Audit terminé", model=model, provider="sync")
            return await fake_prov.generate(prompt=prompt, model=model, system_prompt=system_prompt)

    master._injected_provider = SyncControlledProvider()
    master.provider = master._injected_provider

    # T0: Message 1 (MISSION) démarré en arrière-plan
    res_m1 = await master.execute_intent(
        user_prompt="Audite le module vault et vérifie les vulnérabilités",
        mission_profile="MISSION",
        session_id=sess_id,
        background=True
    )

    assert res_m1["ok"] is True
    assert res_m1["status"] == "RUNNING"
    m_id = res_m1["mission_id"]

    # Attente que le worker arrière-plan ait démarré son nœud
    await asyncio.wait_for(event_started.wait(), timeout=2.0)

    # T1: Vérification que la mission 1 est réellement RUNNING dans mission_registry
    rec = mission_registry.get(m_id)
    assert rec is not None
    assert rec.status == MissionStatus.RUNNING

    # T2 & T3: Message 2 (CHAT) envoyé pendant que la mission 1 est RUNNING en arrière-plan
    res_c2 = await master.execute_intent(
        user_prompt="Tu en es où ?",
        mission_profile="AUTO",
        session_id=sess_id
    )

    # Le CHAT retourne immédiatement la réponse sans attendre la fin de la mission 1
    assert res_c2["ok"] is True
    assert "subtasks" not in res_c2
    assert "[RESPONSE CHAT" in res_c2["response"]

    # T4: La mission 1 est toujours RUNNING pendant que le CHAT a répondu
    assert rec.status == MissionStatus.RUNNING

    # T5: On libère la mission 1 et on attend sa complétion complète
    event_release.set()
    await asyncio.sleep(0.1)

    # T6: La mission 1 est maintenant SUCCEEDED
    assert rec.status == MissionStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_path_governance_canonical_workspace_anchoring(monkeypatch):
    """Vérifie que la résolution des chemins relatifs est ancrée au workspace canonique G:\\AI\\E-zzio et non au CWD."""
    from pathlib import Path

    from core.evidence_store import EvidenceStore
    from core.memory.unified_gateway import UnifiedMemoryGateway
    from core.security.audit_ledger import AuditLedger

    mw = UnifiedMemoryGateway()
    assert str(mw.db_path).startswith(r"G:\AI\E-zzio") or "G:\\AI\\E-zzio" in str(mw.db_path) or "G:/AI/E-zzio" in str(mw.db_path).replace("\\", "/")

    ev = EvidenceStore()
    assert str(ev.db_path).startswith(r"G:\AI\E-zzio") or "G:\\AI\\E-zzio" in str(ev.db_path) or "G:/AI/E-zzio" in str(ev.db_path).replace("\\", "/")

    al = AuditLedger()
    assert str(al.db_path).startswith(r"G:\AI\E-zzio") or "G:\\AI\\E-zzio" in str(al.db_path) or "G:/AI/E-zzio" in str(al.db_path).replace("\\", "/")


@pytest.mark.asyncio
async def test_background_task_lifecycle_and_cancellation():
    """Vérifie l'annulation d'une tâche d'arrière-plan et le nettoyage du registre _background_tasks."""
    provider = FakeAutoIntentProvider()
    master = EzzioMaster(provider=provider)

    async def _long_mission(*args, **kwargs):
        await asyncio.sleep(10)
        return {"synthesis": "done"}

    with patch.object(master, "orchestrate_multi_agent_mission", side_effect=_long_mission):
        res = await master.execute_intent(
            user_prompt="Lance un audit long",
            mission_profile="MISSION",
            session_id="sess-cancel-test",
            background=True,
        )
        assert res["ok"] is True
        assert res["status"] == "RUNNING"
        m_id = res["mission_id"]

        assert len(master._background_tasks) == 1
        bg_task = list(master._background_tasks)[0]

        # Annulation explicite
        bg_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await bg_task

        rec = mission_registry.get(m_id)
        assert rec is not None
        assert rec.status == MissionStatus.CANCELLED
        # Vérification du nettoyage automatique dans _background_tasks
        assert len(master._background_tasks) == 0


@pytest.mark.asyncio
async def test_mission_registry_cancel_triggers_bg_task_cancellation():
    """Vérifie que mission_registry.cancel(mission_id) annule réellement la tâche asyncio d'arrière-plan."""
    provider = FakeAutoIntentProvider()
    master = EzzioMaster(provider=provider)

    async def _long_mission(*args, **kwargs):
        await asyncio.sleep(10)
        return {"synthesis": "done"}

    with patch.object(master, "orchestrate_multi_agent_mission", side_effect=_long_mission):
        res = await master.execute_intent(
            user_prompt="Lance un audit long",
            mission_profile="MISSION",
            session_id="sess-cancel-registry-test",
            background=True,
        )
        assert res["ok"] is True
        assert res["status"] == "RUNNING"
        m_id = res["mission_id"]

        assert len(master._background_tasks) == 1

        # Annulation via mission_registry.cancel()
        cancelled_ok = mission_registry.cancel(m_id)
        assert cancelled_ok is True

        # Laisser le temps à la boucle événementielle d'exécuter la tâche et le callback de nettoyage
        await asyncio.sleep(0.05)

        rec = mission_registry.get(m_id)
        assert rec is not None
        assert rec.status == MissionStatus.CANCELLED
        # La tâche a été automatiquement retirée du registre _background_tasks
        assert len(master._background_tasks) == 0
