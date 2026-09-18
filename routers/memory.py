from fastapi import APIRouter

from core.memory.instance import memory_gateway
from core.schemas import MemoryQuery

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/recent")
async def memory_recent(limit: int = 20):
    items = await memory_gateway.get_session_history(session_id="global", limit=limit)
    return {"items": items}


@router.post("/search")
async def memory_search(query: MemoryQuery):
    results = await memory_gateway.search_memory(query.query, limit=query.limit)
    return results


@router.post("/compact")
async def memory_compact():
    return {"status": "SUCCESS", "engine": "sqlite_wal_fts5"}
