from fastapi import APIRouter
from core.memory import ezzio_memory
from core.schemas import MemoryQuery

router = APIRouter(prefix="/memory", tags=["memory"])

@router.get("/recent")
async def memory_recent():
    return {"items": ezzio_memory.get_context(last_n=20)}

@router.post("/search")
async def memory_search(query: MemoryQuery):
    return {"items": ezzio_memory.search(query.query, limit=query.limit)}

@router.post("/compact")
async def memory_compact():
    return ezzio_memory.compact(keep_last=400)
