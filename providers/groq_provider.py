import asyncio
import time
from typing import Any

import aiohttp

from providers.base_provider import BaseProvider
from providers.key_scheduler import KeyScheduler
from providers.provider_response import ProviderResponse
from providers.provider_telemetry import provider_telemetry
from providers.secrets_loader import get_groq_keys


class GroqProvider(BaseProvider):
    def __init__(self):
        self.scheduler = KeyScheduler(get_groq_keys())
        self.url = "https://api.groq.com/openai/v1/chat/completions"

    def capabilities(self) -> list:
        return ["fast_chat", "realtime_discord", "quick_response", "fallback"]

    def health(self) -> dict[str, Any]:
        active_count = self.scheduler.get_active_count()
        return {
            "provider": "groq",
            "healthy": active_count > 0,
            "status": "OPERATIONAL" if active_count > 0 else "POOL_EXHAUSTED",
            "pool_size": len(self.scheduler.keys),
            "active_keys": active_count,
            "capabilities": self.capabilities(),
        }

    async def generate(
        self,
        prompt: str,
        model: str | None = "llama-3.3-70b-versatile",
        image_bytes: bytes | None = None,
        capability: str = "default",
    ) -> ProviderResponse:
        max_retries = max(len(self.scheduler.keys), 1)

        for attempt in range(max_retries):
            idx, key = await self.scheduler.get_next_key()
            if key is None:
                break

            start_time = time.perf_counter()
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": prompt},
                ],
                "temperature": 0.7,
            }

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(self.url, json=payload, headers=headers, timeout=12) as resp:
                        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                        if resp.status == 200:
                            data = await resp.json()
                            content = data["choices"][0]["message"]["content"]
                            provider_telemetry.record_event("groq", model, capability, True, elapsed_ms, key_index=idx)
                            return ProviderResponse(
                                ok=True,
                                provider="groq",
                                model=model,
                                content=content,
                                latency_ms=round(elapsed_ms, 2),
                                metadata={"key_index": idx},
                            )
                        elif resp.status == 429:
                            self.scheduler.mark_exhausted(idx, 120)
                            provider_telemetry.record_event(
                                "groq", model, capability, False, elapsed_ms, error_type="429", quota_state="exhausted", key_index=idx
                            )
                        elif resp.status in [401, 403]:
                            self.scheduler.mark_invalid(idx)
                            provider_telemetry.record_event("groq", model, capability, False, elapsed_ms, error_type="auth", key_index=idx)
                        else:
                            provider_telemetry.record_event(
                                "groq", model, capability, False, elapsed_ms, error_type=f"http_{resp.status}", key_index=idx
                            )
                        await asyncio.sleep(0.5)
            except Exception:
                provider_telemetry.record_event("groq", model, capability, False, 0.0, error_type="network", key_index=idx)

        provider_telemetry.record_event("groq", model, capability, False, 0.0, error_type="pool_exhausted", quota_state="exhausted")
        return ProviderResponse(ok=False, provider="groq", model=model, error="Épuisement du pool Groq.")
