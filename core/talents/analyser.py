from typing import Any

from core.llm_engine import query_model_async
from core.talents.base_talent import BaseTalent


class Analyser(BaseTalent):
    def __init__(self, name: str = "analyser") -> None:
        super().__init__(name)

    async def run(self, data: Any) -> Any:
        prompt = f"Analyse le contenu suivant de manière concise, factuelle et utile. Signale explicitement les incertitudes.\n\n{data}"

        return await query_model_async(
            prompt,
            organ_key="analysis",
            speed="normal",
        )
