"""
E-ZZIO Core — Unified Facade & Developer SDK.
Offre une interface de haut niveau, solide et consolidée pour interagir avec tous les piliers d'E-ZZIO :
1. Cognition & Chat (ezzio.chat)
2. Passerelle Universelle de Génération (ezzio.generate) : Tableurs (XLSX), Présentations (PPTX), Documents (PDF/DOCX), Archives (ZIP), Audio (WAV), 3D (OBJ), Visuels & Bannières (Pillow), Dev Studio
3. Perception Universelle (ezzio.perceive)
4. Mémoire FTS5 / SQLite (ezzio.search_memory, ezzio.get_history)
5. Registre de Capacités Qualifiées (ezzio.execute_capability)
6. Sécurité & Télémétrie (ezzio.get_status)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from core.capabilities.registry import capability_registry
from core.ezzio_master import ezzio_master
from core.generators.generation_router import generation_router
from core.memory.instance import memory_gateway
from core.models.gemini_pool import MODEL_LIFECYCLE_REGISTRY, gemini_pool
from core.perception.universal_reader import UniversalReader


class EzzioSDK:
    """Façade souveraine consolidant l'ensemble des points d'entrée d'E-ZZIO."""

    def __init__(self, workspace_root: str = "G:\\AI\\E-zzio"):
        self.workspace_root = Path(workspace_root).resolve()
        self.master = ezzio_master
        self.generator = generation_router
        self.reader = UniversalReader()
        self.memory = memory_gateway
        self.capabilities = capability_registry
        self.gemini_pool = gemini_pool

    async def init(self) -> None:
        """Initialise tous les sous-systèmes asynchrones."""
        await self.memory.init()

    async def chat(
        self,
        text: str,
        speed: str = "fast",
        force_cloud: bool = False,
        session_id: str = "default"
    ) -> dict[str, Any]:
        """Échange cognitif avec E-ZZIO (CognitiveGateway + Mémoire + Identité)."""
        await self.init()
        return await self.master.execute_intent(
            user_prompt=text,
            speed=speed,
            force_cloud=force_cloud,
            session_id=session_id
        )

    async def generate(self, user_message: str) -> dict[str, Any]:
        """Génération multimodale universelle à partir d'un prompt en langage naturel."""
        return await self.generator.route_and_generate(user_message=user_message)

    async def perceive(self, path_or_url: str) -> dict[str, Any]:
        """Perception et extraction universelle de documents, médias ou pages web."""
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            return await self.capabilities.execute_capability("crawl4ai-engine", {"target_url": path_or_url})
        return self.reader.read_file(path_or_url)

    async def search_memory(self, query: str, limit: int = 5) -> dict[str, Any]:
        """Recherche dans la mémoire épisodique et sémantique FTS5 SQLite."""
        await self.init()
        return await self.memory.search_memory(query=query, limit=limit)

    async def get_session_history(self, session_id: str = "default", limit: int = 10) -> list[dict[str, Any]]:
        """Récupère l'historique d'une session de conversation."""
        await self.init()
        return await self.memory.get_session_history(session_id=session_id, limit=limit)

    async def execute_capability(self, capability_name: str, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
        """Exécute une capacité externe qualifiée (SaaS, Web, Modèles)."""
        return await self.capabilities.execute_capability(capability_name, parameters or {})

    def get_status(self) -> dict[str, Any]:
        """Retourne l'état complet du système, des capacités et des modèles."""
        return {
            "status": "ONLINE",
            "workspace": str(self.workspace_root),
            "capabilities": self.capabilities.list_capabilities(),
            "models_lifecycle": MODEL_LIFECYCLE_REGISTRY,
            "gemini_projects_count": len(self.gemini_pool.projects)
        }


# Singleton universel exporté
ezzio = EzzioSDK()
