import os

import pytest

from core.rag.simple_rag import SimpleRAG


@pytest.mark.asyncio
async def test_simple_rag():
    db_path = "runtime/rag/test_rag.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    rag = SimpleRAG(db_path)
    await rag.init()

    doc_id = await rag.add_document("Test document content", {"source": "test"})
    assert doc_id == 1

    results = await rag.search_documents("Test")
    assert len(results) == 1
    assert results[0]["content"] == "Test document content"
