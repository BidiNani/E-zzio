import asyncio

import pytest

from core.evidence_store import EvidenceStore
from core.memory.unified_gateway import UnifiedMemoryGateway


@pytest.mark.asyncio
async def test_phase8_memory_5_turns_continuity_and_restart(tmp_path):
    db_file = str(tmp_path / "memory_5turns_p8.db")

    # 1. Premier cycle de vie (Tours 1 à 4)
    gw1 = UnifiedMemoryGateway(db_path=db_file)
    await gw1.init()
    session_id = "SESS_P8_5TURNS"

    # Tour 1 : Fait initial
    await gw1.record_message(session_id, "user", "Le port standard d'E-ZZIO API est 8000.", {"type": "fact"})
    await gw1.record_message(session_id, "assistant", "Noté : port API 8000.", {"type": "ack"})

    # Tour 2 : Question dépendante
    await gw1.record_message(session_id, "user", "Quel port utilise l'API ?", {"type": "query"})
    await gw1.record_message(session_id, "assistant", "L'API utilise le port 8000.", {"type": "answer"})

    # Tour 3 : Résultat de tâche
    await gw1.record_message(session_id, "user", "Exécute l'inspection du port.", {"type": "task"})
    await gw1.record_message(session_id, "assistant", "Inspection terminée : port 8000 ouvert et validé.", {"type": "task_result"})

    # Tour 4 : Rappel de tâche
    await gw1.record_message(session_id, "user", "Quel était le résultat de l'inspection ?", {"type": "task_query"})
    await gw1.record_message(session_id, "assistant", "L'inspection a confirmé que le port 8000 est ouvert et validé.", {"type": "task_answer"})

    # 2. Redémarrage du processus
    gw2 = UnifiedMemoryGateway(db_path=db_file)
    await gw2.init()

    # Tour 5 : Rappel post-restart
    history = await gw2.get_session_history(session_id)
    assert len(history) == 8
    assert "8000" in history[0]["content"]
    assert "ouvert et validé" in history[7]["content"]

    # Recherche FTS5 plein texte post-redémarrage
    search_res = await gw2.search_memory("8000")
    assert len(search_res["chat_history"]) >= 2

@pytest.mark.asyncio
async def test_phase8_research_to_memory_integration(tmp_path):
    db_file = str(tmp_path / "evidence_p8.db")
    store = EvidenceStore(db_path=db_file)
    await store.init()

    task_id = "TASK_P8_RES_001"
    query = "E-ZZIO Sovereign Architecture"

    # 1. Enregistrement d'une preuve de recherche réelle via la méthode store existante
    await store.store(
        query=query,
        provider="gemini",
        mode="google",
        data={"status": "OK", "source": "https://ezzio.ai/docs", "facts": ["Architecture souveraine", "Mémoire SQLite WAL"]},
        task_id=task_id
    )

    # 2. Récupération et intégration
    ev_list = await store.get_by_task(task_id)
    assert len(ev_list) >= 1
    ev = ev_list[0]
    assert ev["provider"] == "gemini"
    assert "Architecture souveraine" in ev["data"]["facts"]
