import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.memory.unified_gateway import UnifiedMemoryGateway
from core.system_cleanup import SystemCleanupService
from core.url_reader import UrlReader
from runtime.core.ezzio_core import EzzioCore

logger = logging.getLogger("ezzio.api.chat")

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])

_memory_gateway = UnifiedMemoryGateway("runtime/evidence/evidence.db")
_core = EzzioCore(memory_gateway=_memory_gateway)
_cleanup_service = SystemCleanupService()


async def init_chat_router():
    await _core.init()
    logger.info("[OK] EzzioCore et MemoryGateway initialisés pour le routeur Chat.")


class ChatRequest(BaseModel):
    message: str = Field(..., description="Message de l'utilisateur")
    user_id: str = Field(default="user_default", description="Identifiant unique utilisateur")
    session_id: str | None = Field(default=None, description="Identifiant de session de conversation")


class ChatResponse(BaseModel):
    response: str
    intent: str
    provider: str
    mode: str
    session_id: str
    data: dict[str, Any] = Field(default_factory=dict)


@router.post("", response_model=ChatResponse)
async def post_chat(payload: ChatRequest):
    msg_lower = payload.message.lower()
    resolved_session = payload.session_id or f"sess_{payload.user_id}"

    # 1. Détection Plan de Nettoyage (Dry Run)
    if "nettoie" in msg_lower and any(kw in msg_lower for kw in ["bruit", "dossier", "nettoyage", "scratch"]):
        try:
            data = _cleanup_service.run_cleanup(dry_run=True, remove_logs=True, remove_temp=True, remove_archives=True)
            folders = data.get("folders_removed", [])
            files = data.get("files_removed", [])
            mb_freed = data.get("space_freed_bytes", 0) / (1024 * 1024)

            plan_lines = ["### 🧹 Plan de Nettoyage Détecté\n"]
            if folders:
                plan_lines.append(f"**Dossiers orphelins ({len(folders)}) :**")
                plan_lines.extend([f"- `{f}`" for f in folders])
            if files:
                plan_lines.append(f"\n**Fichiers temporaires ({len(files)}) :**")
                plan_lines.extend([f"- `{f}`" for f in files[:10]])
                if len(files) > 10:
                    plan_lines.append(f"- *...et {len(files) - 10} autres fichiers.*")

            plan_lines.append(f"\n**Espace estimé à libérer :** `{mb_freed:.2f} MB`")
            plan_lines.append("\nPour confirmer et exécuter la purge réelle, réponds : **'exécute le nettoyage'**.")

            return ChatResponse(
                response="\n".join(plan_lines), intent="system_cleanup_plan", provider="system", mode="command", session_id=resolved_session
            )
        except Exception as e:
            return ChatResponse(
                response=f"Erreur d'analyse : {e}", intent="error", provider="system", mode="command", session_id=resolved_session
            )

    # 2. Détection Exécution Réelle du Nettoyage
    if "exécute" in msg_lower and "nettoyage" in msg_lower:
        try:
            data = _cleanup_service.run_cleanup(dry_run=False, remove_logs=True, remove_temp=True, remove_archives=True)
            folders_count = len(data.get("folders_removed", []))
            files_count = len(data.get("files_removed", []))
            mb_freed = data.get("space_freed_bytes", 0) / (1024 * 1024)

            return ChatResponse(
                response=f"✅ **Nettoyage terminé avec succès !**\n- `{folders_count}` dossiers purgés\n- `{files_count}` fichiers supprimés\n- `{mb_freed:.2f} MB` libérés.",
                intent="system_cleanup_exec",
                provider="system",
                mode="command",
                session_id=resolved_session,
            )
        except Exception as e:
            return ChatResponse(
                response=f"Erreur de suppression : {e}", intent="error", provider="system", mode="command", session_id=resolved_session
            )

    # 3. Ingestion automatique de liens Internet (URL Reader)
    enriched_message = payload.message
    try:
        urls = UrlReader.extract_urls(payload.message)
        if urls:
            scraped_blocks = []
            for u in urls:
                content = await UrlReader.fetch_url_content(u)
                if content:
                    scraped_blocks.append(
                        f"\n--- Contenu extrait de [{u}] ---\n{content[:4000]}\n-----------------------------------------"
                    )
            if scraped_blocks:
                enriched_message += "\n" + "\n".join(scraped_blocks)
    except Exception as e:
        logger.warning("Échec de l'ingestion d'URL : %s", e)

    # 4. Pipeline Cognitif Normal
    try:
        result = await _core.think(user_id=payload.user_id, message=enriched_message, session_id=payload.session_id)
        return ChatResponse(
            response=result.get("response", ""),
            intent=result.get("intent", "local_chat"),
            provider=result.get("provider", "ollama"),
            mode=result.get("mode", "local_chat"),
            session_id=result.get("session_id", resolved_session),
            data=result.get("data", {}),
        )
    except Exception as e:
        logger.error("Échec /api/v1/chat : %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
