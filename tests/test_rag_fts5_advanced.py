import pytest
from core.rag.simple_rag import SimpleRAG


@pytest.mark.asyncio
async def test_rag_fts5_advanced_features(tmp_path):
    db_file = str(tmp_path / "test_rag.db")
    rag = SimpleRAG(db_path=db_file)
    await rag.init()

    # 1. Insertion par lot
    docs = [
        {"content": "Architecture de micro-noyau souverain pour intelligence artificielle.", "tag": "architecture", "metadata": {"author": "E-zzio"}},
        {"content": "Gestionnaire de quotas et protection par jetons de sécurité.", "tag": "security", "metadata": {"level": "high"}},
        {"content": "Indexation mémoire plein texte FTS5 avec BM25 et snippets.", "tag": "memory", "metadata": {"version": 2}},
    ]
    ids = await rag.add_documents(docs)
    assert len(ids) == 3

    # 2. Recherche FTS5 plein texte
    results = await rag.search_documents("FTS5 BM25", limit=5)
    assert len(results) >= 1
    assert "FTS5" in results[0]["content"]
    assert "snippet" in results[0]
    assert results[0]["tag"] == "memory"
    assert results[0]["metadata"]["version"] == 2

    # 3. Recherche avec filtre par tag
    sec_results = await rag.search_documents("sécurité", tag="security")
    assert len(sec_results) == 1
    assert sec_results[0]["tag"] == "security"

    # Filtre tag inexistant -> vide
    no_results = await rag.search_documents("sécurité", tag="non_existent")
    assert len(no_results) == 0

    # 4. Suppression de document
    deleted = await rag.delete_document(ids[0])
    assert deleted is True

    # Vérification après suppression
    post_delete = await rag.search_documents("micro-noyau")
    assert len(post_delete) == 0
