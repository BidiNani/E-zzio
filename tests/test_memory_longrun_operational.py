import asyncio

import pytest

from core.memory.unified_gateway import UnifiedMemoryGateway


@pytest.mark.asyncio
async def test_memory_longrun_operational_sequence(tmp_path):
    db_path = str(tmp_path / "longrun_evidence.db")

    # 1. Première session active
    gw = UnifiedMemoryGateway(db_path=db_path)
    await gw.init()

    sess_a = "SESS_LONGRUN_ALPHA"
    sess_b = "SESS_LONGRUN_BETA"

    # Injection de 100 messages dans la session A
    for i in range(100):
        role = "user" if i % 2 == 0 else "assistant"
        await gw.record_message(
            session_id=sess_a,
            role=role,
            content=f"AlphaMessage_Index_{i:03d}_Payload",
            metadata={"step": i}
        )

    # Injection de 100 messages dans la session B
    for i in range(100):
        role = "user" if i % 2 == 0 else "assistant"
        await gw.record_message(
            session_id=sess_b,
            role=role,
            content=f"BetaMessage_Index_{i:03d}_Payload",
            metadata={"step": i}
        )

    # Vérification du volume avant redémarrage
    h_a = await gw.get_session_history(sess_a, limit=150)
    h_b = await gw.get_session_history(sess_b, limit=150)
    assert len(h_a) == 100
    assert len(h_b) == 100

    # 2. Simulation d'un redémarrage complet de l'application (fermeture & réouverture)
    gw_reopened = UnifiedMemoryGateway(db_path=db_path)
    await gw_reopened.init()

    # Vérification de l'intégrité et de l'isolation post-redémarrage
    reopened_a = await gw_reopened.get_session_history(sess_a, limit=150)
    reopened_b = await gw_reopened.get_session_history(sess_b, limit=150)

    assert len(reopened_a) == 100
    assert len(reopened_b) == 100

    # Isolation stricte A ∩ B = ∅
    contents_a = set(m["content"] for m in reopened_a)
    contents_b = set(m["content"] for m in reopened_b)
    assert len(contents_a.intersection(contents_b)) == 0

    # Vérification FTS5 post-redémarrage
    fts_res = await gw_reopened.search_memory("AlphaMessage_Index_042")
    assert len(fts_res["chat_history"]) >= 1
    assert "AlphaMessage_Index_042" in fts_res["chat_history"][0]["content"]
