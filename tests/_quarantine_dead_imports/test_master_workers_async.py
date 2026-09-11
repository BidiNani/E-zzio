"""
Tests unitaires ciblés pour le Master Conversationnel et les Workers Asynchrones.
Valide les points critiques exigés par le mandat :
1. Conversation normale pendant qu'un worker est actif
2. Détection d'intention et dispatching vers le worker approprié
3. Tâche longue sans bloquer le Master (Master répond immédiatement)
4. Requête d'état réelle "où en est la tâche ?"
5. Notification et enregistrement de fin de mission
6. Annulation sécurisée d'une mission
7. Gestion des états de mission (QUEUED, RUNNING, COMPLETED, CANCELLED)
8. Exécution simultanée de multiples missions
"""
import pytest
import asyncio
from unittest.mock import AsyncMock

from core.ezzio_master import EzzioMaster
from core.agent.mission_controller import (
    MissionRecord,
    MissionStatus,
    mission_registry,
)
from core.agent.worker_fleet import WorkerFleetDispatcher
from core.agent.coder_federation import CoderModelFederationRouter
from core.providers.base_provider import ProviderResponse, CostClass


@pytest.fixture
def mock_federation():
    router = CoderModelFederationRouter(providers={})
    async def fake_execute(prompt, profile, **kwargs):
        return ProviderResponse(
            content=f"Réponse d'architecture pour: {prompt[:30]}",
            role="assistant",
            model="nvidia/nemotron-3-super-120b-a12b",
            provider="nvidia",
            cost_class=CostClass.FREE_ENDPOINT,
            raw={"coder_federation_trace": {"attempts_count": 1}}
        )
    router.execute_task = fake_execute
    return router


@pytest.mark.asyncio
async def test_worker_selection_by_intent():
    """Vérifie la sélection déterministe du bon worker selon le mandat."""
    fleet = WorkerFleetDispatcher()
    assert fleet.select_worker_for_intent("Analyse G:\\AI\\E-zzio et trouve ce qui consomme le plus de disque") == "CLEANING_WORKER"
    assert fleet.select_worker_for_intent("Fais-moi une image du bureau") == "IMAGE_WORKER"
    assert fleet.select_worker_for_intent("Génère un document PDF de rapport") == "DOCUMENT_WORKER"
    assert fleet.select_worker_for_intent("Diagnostic de santé des processus et du port 8001") == "SYSTEM_WORKER"
    assert fleet.select_worker_for_intent("Où est la classe ModelRouter et explore la codebase") == "RESEARCH_WORKER"
    assert fleet.select_worker_for_intent("Crée ce fichier config.json") == "FILE_WORKER"
    assert fleet.select_worker_for_intent("Refais complètement le module de chat") == "CODER_WORKER"


@pytest.mark.asyncio
async def test_master_immediate_response_on_long_task(mock_federation):
    """Vérifie que le Master répond immédiatement sans attendre la fin du worker."""
    master = EzzioMaster(federation_router=mock_federation)
    
    t0 = asyncio.get_event_loop().time()
    res = await master.execute_intent(
        "Analyse G:\\AI\\E-zzio et trouve ce qui consomme le plus de disque.",
        channel="discord"
    )
    duration = asyncio.get_event_loop().time() - t0
    
    # Doit répondre instantanément (< 500ms)
    assert duration < 0.5
    assert res["ok"] is True
    assert res.get("is_async_job") is True
    assert "CLEANING_WORKER" in res["response"]
    assert "RUNNING" in res["response"]
    
    mission_id = res.get("mission")
    assert mission_id is not None
    record = mission_registry.get(mission_id)
    assert record is not None
    assert record.worker_type == "CLEANING_WORKER"

    # Attendre que le worker termine
    if record.async_task:
        await record.async_task
    assert record.status == MissionStatus.COMPLETED
    assert record.progress == 100
    assert len(record.artifacts) >= 1


@pytest.mark.asyncio
async def test_conversational_parallelism_while_worker_running(mock_federation):
    """Scénario critique : utilisateur discute pendant que le worker tourne, puis demande l'état."""
    master = EzzioMaster(federation_router=mock_federation)
    
    # 1. Lance la mission
    launch_res = await master.execute_intent("Analyse mon disque", channel="discord")
    mission_id = launch_res.get("mission")
    assert mission_id is not None
    
    # 2. Pendant ce temps, pose une question générale
    chat_res = await master.execute_intent(
        "Pendant ce temps, explique-moi mon architecture de federation.",
        channel="discord"
    )
    assert chat_res["ok"] is True
    assert "Réponse d'architecture" in chat_res["response"]
    assert chat_res.get("is_async_job") is not True

    # 3. Interroge l'état : "Où en est la tâche ?"
    status_res = await master.execute_intent(f"Où en est la tâche {mission_id} ?", channel="discord")
    assert status_res["ok"] is True
    assert mission_id in status_res["response"]
    assert ("RUNNING" in status_res["response"] or "COMPLETED" in status_res["response"])


@pytest.mark.asyncio
async def test_safe_cancellation():
    """Vérifie l'annulation sécurisée d'une mission active."""
    record = MissionRecord(
        mission_id="mission_TESTCANCEL",
        goal="Tâche de longue durée",
        worker_type="CODER_WORKER",
        status=MissionStatus.RUNNING,
    )
    mission_registry.register(record)

    master = EzzioMaster()
    cancel_res = await master.execute_intent("Annule la tâche TESTCANCEL", channel="web")
    assert cancel_res["ok"] is True
    assert "CANCELLED" in cancel_res["response"]

    updated = mission_registry.get("mission_TESTCANCEL")
    assert updated.status == MissionStatus.CANCELLED


@pytest.mark.asyncio
async def test_multiple_simultaneous_workers():
    """Vérifie l'indépendance de multiples missions asynchrones simultanées."""
    fleet = WorkerFleetDispatcher()
    m1 = MissionRecord(mission_id="m_A", goal="Analyse disque", worker_type="CLEANING_WORKER")
    m2 = MissionRecord(mission_id="m_B", goal="Génère rapport", worker_type="DOCUMENT_WORKER")
    m3 = MissionRecord(mission_id="m_C", goal="Diagnostic système", worker_type="SYSTEM_WORKER")

    mission_registry.register(m1)
    mission_registry.register(m2)
    mission_registry.register(m3)

    # Exécution concurrente
    await asyncio.gather(
        fleet.execute_mission_async(m1),
        fleet.execute_mission_async(m2),
        fleet.execute_mission_async(m3),
    )

    assert m1.status == MissionStatus.COMPLETED
    assert m2.status == MissionStatus.COMPLETED
    assert m3.status == MissionStatus.COMPLETED
    assert len(m1.artifacts) >= 1
    assert len(m2.artifacts) >= 1


@pytest.mark.asyncio
async def test_cancel_with_backend_verifies_real_stop():
    """Backend actif : CANCELLING demandé, CANCELLED seulement après arrêt réel."""
    started = asyncio.Event()
    finished = asyncio.Event()

    async def slow_backend():
        started.set()
        try:
            await asyncio.sleep(30)
        finally:
            finished.set()

    record = MissionRecord(
        mission_id="mission_TESTBACKEND",
        goal="Tâche lente",
        worker_type="CODER_WORKER",
        status=MissionStatus.RUNNING,
    )
    mission_registry.register(record)
    record.async_task = asyncio.create_task(slow_backend())
    await started.wait()

    master = EzzioMaster()
    cancel_res = await master.execute_intent("Annule la tâche TESTBACKEND", channel="web")
    assert cancel_res["ok"] is True
    assert "CANCELLING" in cancel_res["response"]
    assert "CANCELLED" not in cancel_res["response"].replace("CANCELLING", "")
    assert mission_registry.get("mission_TESTBACKEND").status == MissionStatus.CANCELLING

    await asyncio.wait_for(asyncio.wait([record.async_task]), timeout=5)
    assert finished.is_set()
    assert mission_registry.get("mission_TESTBACKEND").status == MissionStatus.CANCELLED


@pytest.mark.asyncio
async def test_pause_honestly_not_supported(mock_federation):
    """Pause sans backend réel : NOT_SUPPORTED, jamais d'état simulé."""
    master = EzzioMaster(federation_router=mock_federation)
    res = await master.execute_intent("Mets en pause la tâche", channel="web")
    assert res["ok"] is True
    assert "NOT_SUPPORTED" in res["response"]


@pytest.mark.asyncio
async def test_storm_no_leak_no_deadlock(mock_federation):
    """Tempête : 5 tâches + statuts rapides + 2 cancels → 0 fuite, 0 deadlock."""
    master = EzzioMaster(federation_router=mock_federation)
    recs = []
    for i in range(5):
        rec = MissionRecord(mission_id=f"mission_STORM{i}", goal=f"job {i}",
                            worker_type="CODER_WORKER", status=MissionStatus.RUNNING)
        mission_registry.register(rec)

        async def backend():
            try:
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                pass
        rec.async_task = asyncio.create_task(backend())
        recs.append(rec)

    for _ in range(5):  # rafale de statuts pendant la charge
        r = await master.execute_intent("Où en sont les tâches ?", channel="web")
        assert r["ok"] is True

    await master.execute_intent("Annule la tâche STORM0", channel="web")
    await master.execute_intent("Annule la tâche STORM1", channel="web")
    for rec in recs[2:]:  # les autres via le registre (même cycle vérifié)
        assert mission_registry.cancel(rec.mission_id) is True
    await asyncio.wait_for(asyncio.wait([r.async_task for r in recs]), timeout=10)

    states = {mission_registry.get(r.mission_id).status for r in recs}
    assert states <= {MissionStatus.CANCELLED}
    pending = [t for t in asyncio.all_tasks() if not t.done()
               and "STORM" in str(t.get_name())]
    assert pending == []
    for r in recs:
        mission_registry._missions.pop(r.mission_id, None)


@pytest.mark.asyncio
async def test_truth_gate_marks_unverified_factual_answer(mock_federation,
                                                          monkeypatch):
    """Recherche live en échec → repli fédération + mention [Non vérifié]."""
    import core.research_router as _rr

    async def _boom(query, providers=None, memory_hits=None):
        raise RuntimeError("source indisponible (test)")

    monkeypatch.setattr(_rr, "run_adaptive_research", _boom)
    master = EzzioMaster(federation_router=mock_federation)
    res = await master.execute_intent("Est-ce vrai que le modèle X existe ?",
                                      channel="web")
    assert res["ok"] is True
    assert "[Non vérifié]" in res["response"]
    assert res["truth_gate"] == "UNVERIFIED_NO_EVIDENCE"


@pytest.mark.asyncio
async def test_truth_gate_quiet_on_dialogue(mock_federation):
    """Dialogue non factuel → aucune mention, verdict PASS_NON_FACTUAL."""
    master = EzzioMaster(federation_router=mock_federation)
    res = await master.execute_intent("Bonjour, comment vas-tu ?",
                                      channel="web")
    assert res["ok"] is True
    assert "[Non vérifié]" not in res["response"]
    assert res["truth_gate"] == "PASS_NON_FACTUAL"


@pytest.mark.asyncio
async def test_routing_decision_present_on_all_paths(mock_federation):
    """Observabilité §65 : chaque réponse porte sa décision de routage."""
    master = EzzioMaster(federation_router=mock_federation)
    res = await master.execute_intent("Bonjour, comment vas-tu ?",
                                      channel="web")
    rd = res.get("routing_decision", {})
    assert rd.get("action") == "ANSWER"
    assert rd.get("intent") and rd.get("bna") and rd.get("reason")


@pytest.mark.asyncio
async def test_status_miss_fixed(mock_federation):
    """Défaut démontré : 'Où en sont les tâches ?' routé STATUS (ex-conversation)."""
    master = EzzioMaster(federation_router=mock_federation)
    res = await master.execute_intent("Où en sont les tâches ?",
                                      channel="web")
    assert res["routing_decision"]["action"] == "STATUS"
    assert res["ok"] is True


@pytest.mark.asyncio
async def test_ask_on_priority_change(mock_federation):
    """MODIFY sans contrat → ASK déterminsite, 0 appel LLM."""
    master = EzzioMaster(federation_router=mock_federation)
    res = await master.execute_intent("change la priorité de la tâche",
                                      channel="web")
    assert res["routing_decision"]["action"] == "ASK"
    assert res["mission"] == "ASK_QUERY"
    assert "ne pas deviner" in res["response"]


@pytest.mark.asyncio
async def test_bna_cancel_maps_to_cancel_handler(mock_federation):
    """BNA CANCEL exécuté = handler cancel (décision == exécution)."""
    from core.agent.mission_controller import MissionRecord, MissionStatus
    master = EzzioMaster(federation_router=mock_federation)
    rec = MissionRecord(mission_id="mission_PROP1", goal="prop",
                        worker_type="CODER_WORKER",
                        status=MissionStatus.RUNNING)
    mission_registry.register(rec)
    try:
        res = await master.execute_intent("Annule la tâche PROP1",
                                          channel="web")
        assert res["routing_decision"]["action"] == "CANCEL"
        assert res["routing_decision"]["bna"] == "COMMAND"
    finally:
        mission_registry._missions.pop("mission_PROP1", None)


def test_property_cancelled_never_completes():
    """§39 : CANCELLED ne peut pas devenir COMPLETED sans nouvelle exécution."""
    from core.agent.mission_controller import MissionRecord, MissionStatus
    rec = MissionRecord(mission_id="mission_SEAL", goal="seal",
                        worker_type="CODER_WORKER",
                        status=MissionStatus.CANCELLED)
    mission_registry.register(rec)
    try:
        assert mission_registry.cancel("mission_SEAL") is False
        assert mission_registry.get("mission_SEAL").status == MissionStatus.CANCELLED
    finally:
        mission_registry._missions.pop("mission_SEAL", None)


def test_property_double_cancel_idempotent():
    """§41 : rejouer cancel ne crée ni doublon ni corruption."""
    from core.agent.mission_controller import MissionRecord, MissionStatus
    rec = MissionRecord(mission_id="mission_IDEM", goal="idem",
                        worker_type="CODER_WORKER",
                        status=MissionStatus.RUNNING)
    mission_registry.register(rec)
    try:
        first = mission_registry.cancel("mission_IDEM")
        second = mission_registry.cancel("mission_IDEM")
        assert first is True and second is False
        st = mission_registry.get("mission_IDEM").status
        assert st in (MissionStatus.CANCELLED, MissionStatus.CANCELLING)
    finally:
        mission_registry._missions.pop("mission_IDEM", None)


@pytest.mark.asyncio
async def test_failure_injection_cancel_unknown_id(mock_federation):
    """§40 : cancel d'un ID inexistant → message honnête, ok=True, 0 crash."""
    master = EzzioMaster(federation_router=mock_federation)
    res = await master.execute_intent("Annule la tâche ZZZZ99", channel="web")
    assert res["ok"] is True
    assert "Impossible de localiser" in res["response"]


@pytest.fixture
def isolated_registry():
    """Isole le registre global partagé (missions fire-and-forget d'autres
    tests). Restauration garantie, objets records intacts."""
    backup = dict(mission_registry._missions)
    mission_registry._missions.clear()
    try:
        yield
    finally:
        mission_registry._missions.clear()
        mission_registry._missions.update(backup)


@pytest.mark.asyncio
async def test_f1_factual_status_stays_honest(mock_federation,
                                             isolated_registry):
    """F1 : 'statut du projet de loi' → STATUS honnête (0 fabrication),
    suggestion de reformulation ; le routage est tracé. Le gate lexical
    (Wave 3.5) ne reconnaissant pas 'statut de X', aucun contournement
    n'est introduit : DEFERRED au vocabulaire du gate."""
    master = EzzioMaster(federation_router=mock_federation)
    res = await master.execute_intent("statut du projet de loi sur le climat",
                                      channel="web")
    assert res["routing_decision"]["action"] == "STATUS"
    assert "Aucune mission" in res["response"]
    assert "reformulez en question factuelle" in res["response"]
    assert "climat" not in res["response"].split("reformulez")[0]


@pytest.mark.asyncio
async def test_f2_bare_cancel_multi_tasks_asks(mock_federation):
    """F2 : 'annule' nu + 2 actives → ASK, 0 annulation arbitraire."""
    from core.agent.mission_controller import MissionRecord, MissionStatus
    master = EzzioMaster(federation_router=mock_federation)
    for mid in ("mission_F2A", "mission_F2B"):
        mission_registry.register(MissionRecord(
            mission_id=mid, goal="f2", worker_type="CODER_WORKER",
            status=MissionStatus.RUNNING))
    try:
        res = await master.execute_intent("annule", channel="web")
        assert res["routing_decision"]["action"] == "CANCEL"
        assert "Plusieurs tâches" in res["response"]
        assert mission_registry.get("mission_F2A").status == MissionStatus.RUNNING
        assert mission_registry.get("mission_F2B").status == MissionStatus.RUNNING
    finally:
        for mid in ("mission_F2A", "mission_F2B"):
            mission_registry._missions.pop(mid, None)


@pytest.mark.asyncio
async def test_f3_cancel_all_scope(mock_federation, isolated_registry):
    """F3 : 'annule tout' → toutes les actives + compte rendu exact."""
    from core.agent.mission_controller import MissionRecord, MissionStatus
    master = EzzioMaster(federation_router=mock_federation)
    for mid in ("mission_F3A", "mission_F3B"):
        mission_registry.register(MissionRecord(
            mission_id=mid, goal="f3", worker_type="CODER_WORKER",
            status=MissionStatus.RUNNING))
    try:
        res = await master.execute_intent("annule tout", channel="web")
        assert "2 mission(s)" in res["response"]
        assert mission_registry.get("mission_F3A").status == MissionStatus.CANCELLED
        assert mission_registry.get("mission_F3B").status == MissionStatus.CANCELLED
    finally:
        for mid in ("mission_F3A", "mission_F3B"):
            mission_registry._missions.pop(mid, None)


@pytest.mark.asyncio
async def test_status_family_from_real_state(mock_federation,
                                               isolated_registry):
    """§7-8 : famille statut → STATUS, états réels, 0 progression inventée."""
    from core.agent.mission_controller import MissionRecord, MissionStatus
    master = EzzioMaster(federation_router=mock_federation)
    mission_registry.register(MissionRecord(
        mission_id="mission_SF", goal="sf", worker_type="CODER_WORKER",
        status=MissionStatus.RUNNING))
    try:
        for prompt in ("où en est mon travail", "ça avance ?",
                       "Quel est le statut ?", "état des tâches",
                       "qu'est-ce qui bloque", "état du travail"):
            res = await master.execute_intent(prompt, channel="web")
            assert res["routing_decision"]["action"] in ("STATUS", "ASK"), prompt
            if res["routing_decision"]["action"] == "STATUS":
                assert "mission_SF" in res["response"]
                assert "%" not in res["response"]
    finally:
        mission_registry._missions.pop("mission_SF", None)


@pytest.mark.asyncio
async def test_research_reachable_through_classifier(mock_federation):
    """§31 : question info hors-tâche → SEARCH/ANSWER, jamais ASK bloquant."""
    master = EzzioMaster(federation_router=mock_federation)
    res = await master.execute_intent("Quelle est la dernière version de Python ?",
                                      channel="web")
    assert res["routing_decision"]["action"] in ("SEARCH", "ANSWER",
                                                 "ANSWER_FALLBACK")


def test_bna_is_pure_arbiter():
    """§9 : BNA n'exécute rien (aucune mutation registry/moteur)."""
    from core.capabilities.workspace_decisions import DecisionState, best_next_action
    before = [m.mission_id for m in mission_registry.list_missions(limit=100)]
    states = [
        DecisionState(has_answer=True, needs_external_info=True),
        DecisionState(has_answer=False, needs_specialist=True),
        DecisionState(has_answer=False, cancel_requested=True),
        DecisionState(has_answer=False, ambiguous=True),
    ]
    actions = {best_next_action(s)[0].value for s in states}
    after = [m.mission_id for m in mission_registry.list_missions(limit=100)]
    assert actions == {"SEARCH", "DELEGATE", "CANCEL", "ASK"}
    assert before == after


@pytest.mark.asyncio
async def test_barge_in_does_not_cancel(mock_federation):
    """§15/§36 : dialogue pendant tâche RUNNING → tâche intacte."""
    from core.agent.mission_controller import MissionRecord, MissionStatus
    master = EzzioMaster(federation_router=mock_federation)
    mission_registry.register(MissionRecord(
        mission_id="mission_BI", goal="bi", worker_type="CODER_WORKER",
        status=MissionStatus.RUNNING))
    try:
        res = await master.execute_intent("Bonjour, toujours là ?", channel="web")
        assert res["ok"] is True
        assert mission_registry.get("mission_BI").status == MissionStatus.RUNNING
        res2 = await master.execute_intent("Annule la tâche BI", channel="web")
        assert mission_registry.get("mission_BI").status == MissionStatus.CANCELLED
    finally:
        mission_registry._missions.pop("mission_BI", None)


def test_adversarial_cancel_sequences():
    """§27 : cancel/cancel/pause-like/re-cancel → transitions valides seules."""
    from core.agent.mission_controller import MissionRecord, MissionStatus
    rec = MissionRecord(mission_id="mission_ADV", goal="adv",
                        worker_type="CODER_WORKER", status=MissionStatus.RUNNING)
    mission_registry.register(rec)
    try:
        assert mission_registry.cancel("mission_ADV") is True
        assert mission_registry.cancel("mission_ADV") is False
        assert mission_registry.cancel("mission_ADV") is False
        assert mission_registry.cancel("mission_NOPE") is False
        st = mission_registry.get("mission_ADV").status
        assert st == MissionStatus.CANCELLED
    finally:
        mission_registry._missions.pop("mission_ADV", None)


@pytest.mark.asyncio
async def test_concurrent_cancel_and_status(mock_federation):
    """§28 : cancel B + status simultanés → A≠B, états propres."""
    import asyncio
    from core.agent.mission_controller import MissionRecord, MissionStatus
    master = EzzioMaster(federation_router=mock_federation)
    for mid in ("mission_CC1", "mission_CC2"):
        mission_registry.register(MissionRecord(
            mission_id=mid, goal="cc", worker_type="CODER_WORKER",
            status=MissionStatus.RUNNING))
    try:
        r_cancel, r_status = await asyncio.gather(
            master.execute_intent("Annule la tâche CC2", channel="web"),
            master.execute_intent("Où en sont les tâches ?", channel="web"))
        assert mission_registry.get("mission_CC1").status == MissionStatus.RUNNING
        assert mission_registry.get("mission_CC2").status == MissionStatus.CANCELLED
        assert r_cancel["routing_decision"]["action"] == "CANCEL"
        assert r_status["routing_decision"]["action"] == "STATUS"
    finally:
        for mid in ("mission_CC1", "mission_CC2"):
            mission_registry._missions.pop(mid, None)


@pytest.mark.asyncio
async def test_f6_plural_status_lists_all(mock_federation):
    """F6 : 'Où en sont les tâches ?' → TOUTES les actives, 0 silence."""
    from core.agent.mission_controller import MissionRecord, MissionStatus
    master = EzzioMaster(federation_router=mock_federation)
    for mid in ("mission_F6A", "mission_F6B"):
        mission_registry.register(MissionRecord(
            mission_id=mid, goal="f6", worker_type="CODER_WORKER",
            status=MissionStatus.RUNNING))
    try:
        res = await master.execute_intent("Où en sont les tâches ?",
                                          channel="web")
        assert res["routing_decision"]["action"] == "STATUS"
        assert "mission_F6A" in res["response"]
        assert "mission_F6B" in res["response"]
        n = len(master.registry.list_active())
        assert f"({n})" in res["response"]
    finally:
        for mid in ("mission_F6A", "mission_F6B"):
            mission_registry._missions.pop(mid, None)
