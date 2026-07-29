from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.system import router as system_router
from routers.chat import router as chat_router
from routers.memory import router as memory_router
from routers.actions import router as actions_router
from routers.models import router as models_router
from routers.autonomy import router as autonomy_router

app = FastAPI(title="E-ZZIO API", version="v2.6-autonomic-tactical-core")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system_router)
app.include_router(chat_router)
app.include_router(memory_router)
app.include_router(actions_router)
app.include_router(models_router)
app.include_router(autonomy_router)
