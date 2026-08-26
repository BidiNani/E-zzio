from pathlib import Path
import pytest
from core.evidence.store import EvidenceStore


@pytest.mark.asyncio
async def test_evidence_store(tmp_path: Path):
    test_db = str(tmp_path / "test_evidence.db")
    store = EvidenceStore(test_db)
    await store.init()

    await store.store(query="test query", provider="test_provider", mode="fast", data={"result": "test"}, task_id="test_123")

    results = await store.get_by_task("test_123")
    assert len(results) == 1
    assert results[0]["query"] == "test query"
    assert results[0]["provider"] == "test_provider"
    assert results[0]["task_id"] == "test_123"
    assert results[0]["data"] == {"result": "test"}
