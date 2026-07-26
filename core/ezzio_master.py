import asyncio
from core.dispatcher import ezzio_dispatcher
from core.memory import ezzio_memory
from core import safe_actions
import sys
from pathlib import Path

# Import direct robuste du broker cloud
sys.path.append(str(Path("G:/AI/E-zzio/core")))
import cloud_brain_broker

class EzzioMasterOrchestrator:
    def __init__(self):
        self.dispatcher = ezzio_dispatcher
        self.memory = ezzio_memory
        self.ledger = safe_actions.ledger
        self.cloud_chat = cloud_brain_broker.cloud_chat

    async def execute_intent(self, user_prompt: str, speed: str = "auto", force_cloud: bool = False):
        organ_key, organ_info, score, hits = self.dispatcher.select_organ(user_prompt)
        selected_model = self.dispatcher.select_model_for_speed(organ_info, speed)
        
        use_cloud = force_cloud or (organ_info.get("priority", 1) >= 8 and "code" in user_prompt.lower())
        
        if use_cloud:
            try:
                cloud_res = self.cloud_chat(text=user_prompt, provider="gemini")
                response = cloud_res.get("reply") or str(cloud_res)
                source = "Gemini Pro (Cloud - Super Cerveau)"
            except Exception as e:
                response = await self.dispatcher.route_detailed_async(user_prompt, speed=speed)
                source = f"Ollama Local (Fallback CPU - {selected_model}) [Erreur Cloud: {e}]"
        else:
            response = await self.dispatcher.route_detailed_async(user_prompt, speed=speed)
            source = f"Ollama Local (Ryzen 9 CPU - {selected_model})"

        self.memory.save_interaction(user_prompt, str(response), organ_key)

        return {
            "organ": organ_key,
            "source": source,
            "response": response
        }

ezzio_master = EzzioMasterOrchestrator()
