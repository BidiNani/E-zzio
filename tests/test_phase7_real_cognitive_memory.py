import asyncio

import pytest

from core.memory.unified_gateway import UnifiedMemoryGateway


@pytest.mark.asyncio
async def test_phase7_cognitive_memory_multi_turn_and_restart(tmp_path):
    db_file = str(tmp_path / "cognitive_p7.db")

    # 1. Premier cycle actif : 3 tours conversationnels et factuels
    gw1 = UnifiedMemoryGateway(db_path=db_file)
    await gw1.init()

    session_id = "SESS_P7_COGNITIVE"

    # TOUR 1 : Enregistrement d'une information factuelle
    await gw1.record_message(
        session_id=session_id,
        role="user",
        content="Mon nom de code est Operateur-42 et je gère le projet E-ZZIO.",
        metadata={"fact": "identity"}
    )

    # TOUR 2 : Question nécessitant l'information
    await gw1.record_message(
        session_id=session_id,
        role="assistant",
        content="Bien reçu, Opérateur-42.",
        metadata={"fact": "acknowledgement"}
    )

    # TOUR 3 : Enregistrement de synthèse
    await gw1.record_message(
        session_id=session_id,
        role="user",
        content="Quelle est ma fonction principale ?",
        metadata={"query": "role"}
    )
    await gw1.record_message(
        session_id=session_id,
        role="assistant",
        content="Vous êtes l'Opérateur-42 en charge du pilotage souverain d'E-ZZIO.",
        metadata={"synthesis": True}
    )

    # 2. Simulation d'arrêt et de redémarrage complet du processus
    gw2 = UnifiedMemoryGateway(db_path=db_file)
    await gw2.init()

    # Vérification de la persistance post-redémarrage
    history = await gw2.get_session_history(session_id)
    assert len(history) == 4
    assert "Operateur-42" in history[0]["content"]
    assert "pilotage souverain" in history[3]["content"]

    # Recherche FTS5 post-redémarrage
    search_res = await gw2.search_memory("Operateur-42")
    assert len(search_res["chat_history"]) >= 1
    assert any("E-ZZIO" in m["content"] for m in search_res["chat_history"])
