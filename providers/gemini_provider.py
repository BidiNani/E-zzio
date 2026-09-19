import asyncio
import time
from typing import Any

from google import genai
from google.genai import types

from providers.base_provider import BaseProvider
from providers.key_scheduler import KeyScheduler
from providers.provider_response import ProviderResponse
from providers.provider_telemetry import provider_telemetry
from providers.secrets_loader import get_gemini_keys

GEMINI_MODELS = [
    "gemini-3.7-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-pro-preview",
    "gemini-3.6-flash",
    "gemini-3.1-flash-lite",
]


class GeminiProvider(BaseProvider):
    def __init__(self):
        self.scheduler = KeyScheduler(get_gemini_keys())

    def capabilities(self) -> list[str]:
        return ["reasoning", "architecture", "vision", "web_grounding", "deep_analysis"]

    def health(self) -> dict[str, Any]:
        active_count = self.scheduler.get_active_count()
        return {
            "provider": "gemini",
            "healthy": active_count > 0,
            "status": "OPERATIONAL" if active_count > 0 else "POOL_EXHAUSTED",
            "pool_size": len(self.scheduler.keys),
            "active_keys": active_count,
            "capabilities": self.capabilities(),
        }

    async def generate(
        self, prompt: str, model: str | None = "gemini-3.7-flash", image_bytes: bytes | None = None, capability: str = "default"
    ) -> ProviderResponse:
        target_model = model if model in GEMINI_MODELS else GEMINI_MODELS[0]
        max_retries = max(len(self.scheduler.keys), 1)
        loop = asyncio.get_running_loop()

        for _attempt in range(max_retries):
            idx, key = await self.scheduler.get_next_key()
            if key is None:
                break

            start_time = time.perf_counter()
            try:
                client = genai.Client(api_key=key)
                contents = [types.Part.from_text(text=prompt)]
                if image_bytes:
                    contents.append(types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"))

                response = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: client.models.generate_content(
                            model=target_model,
                            contents=contents,
                            config=types.GenerateContentConfig(tools=[{"google_search": {}}], temperature=0.8, max_output_tokens=8192),
                        ),
                    ),
                    timeout=12.0,
                )
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                reply = response.text if response and response.text else ""

                provider_telemetry.record_event(
                    "gemini", target_model, capability, True, elapsed_ms, quota_state="available", key_index=idx
                )
                return ProviderResponse(
                    ok=True,
                    provider="gemini",
                    model=target_model,
                    content=reply,
                    latency_ms=round(elapsed_ms, 2),
                    metadata={"key_index": idx},
                )

            except TimeoutError:
                provider_telemetry.record_event("gemini", target_model, capability, False, 12000.0, error_type="timeout", key_index=idx)
                await asyncio.sleep(0.5)
            except Exception as e:
                err_str = str(e)
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    self.scheduler.mark_exhausted(idx, 3600)
                    provider_telemetry.record_event(
                        "gemini", target_model, capability, False, elapsed_ms, error_type="429", quota_state="exhausted", key_index=idx
                    )
                elif "401" in err_str or "403" in err_str or "API_KEY_INVALID" in err_str:
                    self.scheduler.mark_invalid(idx)
                    provider_telemetry.record_event("gemini", target_model, capability, False, elapsed_ms, error_type="auth", key_index=idx)
                else:
                    provider_telemetry.record_event(
                        "gemini", target_model, capability, False, elapsed_ms, error_type="network", key_index=idx
                    )
                await asyncio.sleep(0.5)

        provider_telemetry.record_event(
            "gemini", target_model, capability, False, 0.0, error_type="pool_exhausted", quota_state="exhausted"
        )
        return ProviderResponse(ok=False, provider="gemini", model=target_model, error="Épuisement du pool Gemini.")
