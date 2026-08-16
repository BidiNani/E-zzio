import logging
from typing import Any, Dict, Optional
from core.memory.unified_gateway import UnifiedMemoryGateway
from core.router.intent_router import IntentRouter, IntentType
from core.decision_router import DecisionRouter, SearchMode
from core.providers.ollama_provider import OllamaProvider
from core.providers.gemini_provider import GeminiProvider
from core.security.guardrail import PromptGuard, SecurityViolationError
from core.security.quota_manager import QuotaExceededError

logger = logging.getLogger("ezzio.core")

class EzzioCore:
    def __init__(self, memory_gateway: UnifiedMemoryGateway, quota_manager=None, decision_router=None):
        self.memory = memory_gateway
        self.intent_router = IntentRouter()
        self.decision_router = decision_router or DecisionRouter([OllamaProvider(), GeminiProvider()])
        self.quota_manager = quota_manager
        self.guard = PromptGuard()

    async def init(self):
        await self.memory.init()

    async def think(self, user_id: str, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        sanitized_message = self.guard.sanitize(message)
        effective_session = session_id or f"sess_{user_id}"
        await self.memory.record_message(effective_session, "user", sanitized_message)

        classification = self.intent_router.classify(sanitized_message)
        intent = classification.get("intent", IntentType.LOCAL_CHAT)
        target_provider = classification.get("target_provider", "ollama")

        intent_mode_map = {
            IntentType.LOCAL_CHAT: "local_chat",
            IntentType.WEB_SEARCH: "web_search",
            IntentType.DEEP_REASONING: "deep_reasoning",
            IntentType.MEMORY_QUERY: "memory_recall"
        }
        expected_mode = intent_mode_map.get(intent, "local_chat")

        response_text = ""
        used_provider = target_provider
        mode_used = expected_mode

        if intent == IntentType.DEEP_REASONING:
            try:
                if self.quota_manager:
                    await self.quota_manager.check_and_increment(user_id, "gemini")
                res = await self.decision_router.search(sanitized_message, mode=SearchMode.GOOGLE)
                response_text = res.get("data", {}).get("text", "")
                used_provider = res.get("provider", "gemini")
            except (QuotaExceededError, Exception) as e:
                logger.warning(f"[*] Fallback local déclenché pour Deep Reasoning ({e})")
                res = await self.decision_router.search(sanitized_message, mode=SearchMode.LOCAL)
                response_text = res.get("data", {}).get("text", "")
                used_provider = res.get("provider", "ollama")
                mode_used = "local_fallback"
        elif intent == IntentType.WEB_SEARCH:
            try:
                if self.quota_manager:
                    await self.quota_manager.check_and_increment(user_id, "tavily")
                res = await self.decision_router.search(sanitized_message, mode=SearchMode.FAST)
                response_text = res.get("data", {}).get("text", "")
                used_provider = res.get("provider", "tavily")
            except (QuotaExceededError, Exception):
                res = await self.decision_router.search(sanitized_message, mode=SearchMode.LOCAL)
                response_text = res.get("data", {}).get("text", "")
                used_provider = res.get("provider", "ollama")
                mode_used = "local_search_fallback"
        else:
            mode = SearchMode.LOCAL if target_provider == "ollama" else SearchMode.FAST
            res = await self.decision_router.search(sanitized_message, mode=mode)
            response_text = res.get("data", {}).get("text", "")
            used_provider = res.get("provider", target_provider)

        await self.memory.record_message(
            effective_session,
            "assistant",
            response_text,
            metadata={"provider": used_provider, "intent": intent.value, "mode": mode_used}
        )
        return {
            "response": response_text,
            "intent": intent.value,
            "provider": used_provider,
            "mode": mode_used
        }
