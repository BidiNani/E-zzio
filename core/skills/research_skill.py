from typing import Any

from core.decision_router import DecisionRouter, SearchMode
from core.evidence_store import EvidenceStore


class ResearchSkill:
    def __init__(self, router: DecisionRouter, evidence_store: EvidenceStore):
        self.router = router
        self.evidence_store = evidence_store

    async def search(
        self, query: str, mode: SearchMode = SearchMode.FAST, task_id: str = None, user_id: str = None, channel_id: str = None
    ) -> dict[str, Any]:
        # Exécuter la recherche
        result = await self.router.search(query, mode=mode)

        # Stocker dans l'evidence store
        await self.evidence_store.store(
            query=query,
            provider=result["provider"],
            mode=result["mode"],
            data=result["data"],
            task_id=task_id,
            user_id=user_id,
            channel_id=channel_id,
        )

        return result
