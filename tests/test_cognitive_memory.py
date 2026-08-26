import pytest
import asyncio
from core.memory.unified_gateway import UnifiedMemoryGateway

@pytest.mark.asyncio
async def test_cognitive_memory_three_levels_and_provenance(tmp_path):
    db_path = str(tmp_path / "cognitive_evidence.db")
    gw = UnifiedMemoryGateway(db_path=db_path)
    await gw.init()
    
    sess_id = "SESS_COGNITIVE_001"
    
    # 1. Niveau Conversationnel : Tour de parole standard
    await gw.record_message(
        session_id=sess_id,
        role="user",
        content="Mon projet s'appelle E-ZZIO et vise la souveraineté IA.",
        metadata={"level": "conversational", "timestamp": 1724342400}
    )
    
    # 2. Niveau Factuel : Enregistrement d'un fait clé
    await gw.record_message(
        session_id=sess_id,
        role="assistant",
        content="Bien noté : le projet se nomme E-ZZIO.",
        metadata={"level": "factual", "fact_key": "project_name", "fact_val": "E-ZZIO"}
    )
    
    # 3. Niveau Preuve (Evidence) : Indexation FTS5 et recherche
    search_res = await gw.search_memory("souveraineté")
    assert len(search_res["chat_history"]) >= 1
    found = search_res["chat_history"][0]
    assert "E-ZZIO" in found["content"]
    assert "souveraineté" in found["content"]
    
    # 4. Vérification de l'isolation du scope par rapport à une autre session
    other_sess = "SESS_COGNITIVE_OTHER"
    await gw.record_message(
        session_id=other_sess,
        role="user",
        content="Mon projet s'appelle Projet-XYZ.",
        metadata={"level": "conversational"}
    )
    
    hist_main = await gw.get_session_history(sess_id)
    hist_other = await gw.get_session_history(other_sess)
    
    assert all("Projet-XYZ" not in m["content"] for m in hist_main)
    assert all("E-ZZIO" not in m["content"] for m in hist_other)
