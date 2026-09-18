"""E-ZZIO Core — Groq Cloud Federated Provider (Phase 6.2).

Implements BaseFederatedProvider for Groq Cloud API with multi-key rotation and quota failover support.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
from pathlib import Path

from core.cognition.model_federation.base_provider import (
    BaseFederatedProvider,
    FederatedTaskRequest,
    FederatedTaskResult,
    ProviderDomain,
)
from core.cognition.providers.key_pool import SovereignKeyPool

logger = logging.getLogger(__name__)


class GroqFederatedProvider(BaseFederatedProvider):
    DEFAULT_MODEL = "llama-3.3-70b-versatile"
    API_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, key_pool: SovereignKeyPool, root_dir: Path = Path(r"G:\AI\E-zzio")):
        self.root_dir = root_dir
        self.key_pool = key_pool

    @property
    def domain(self) -> ProviderDomain:
        return ProviderDomain.CLOUD_GROQ

    def is_available(self) -> bool:
        return self.key_pool.get_pool_health()["active_keys"] > 0

    def execute(self, request: FederatedTaskRequest) -> FederatedTaskResult:
        model = request.context_metadata.get("model", self.DEFAULT_MODEL)
        max_attempts = len(self.key_pool.slots) if self.key_pool.slots else 1

        for _ in range(max_attempts):
            idx, raw_key, masked_key = self.key_pool.get_next_key()
            if raw_key is None:
                return FederatedTaskResult(
                    task_id=request.task_id,
                    provider_domain=self.domain,
                    model_name=model,
                    status="FAILED",
                    content="",
                    execution_duration_ms=0.0,
                    error_message="All Groq API keys exhausted (429 Rate-Limited or Quota).",
                )

            start = time.perf_counter()
            headers = {
                **({"Authorization": f"Bearer {raw_key}"} if raw_key and str(raw_key).strip() else {}),
                "Content-Type": "application/json",
                "User-Agent": "E-ZZIO-Sovereign-Core/9.0",
            }
            body = {
                "model": model,
                "messages": [
                    {"role": "system", "content": request.prompt},
                ],
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            }

            req = urllib.request.Request(self.API_URL, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")

            try:
                with urllib.request.urlopen(req, timeout=request.timeout_seconds) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    elapsed_ms = (time.perf_counter() - start) * 1000.0
                    self.key_pool.mark_success(idx)
                    return FederatedTaskResult(
                        task_id=request.task_id,
                        provider_domain=self.domain,
                        model_name=model,
                        status="SUCCESS",
                        content=text,
                        execution_duration_ms=elapsed_ms,
                        raw_response_payload={"masked_key": masked_key, "choices_count": len(data.get("choices", []))},
                    )
            except urllib.error.HTTPError as he:
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                if he.code == 429:
                    self.key_pool.mark_rate_limited(idx, ttl_seconds=60.0, error_code=429)
                    logger.warning(f"[GROQ PROVIDER] Slot {masked_key} received 429. Rotating to next slot.")
                elif he.code in {401, 403}:
                    self.key_pool.mark_auth_failed(idx, error_code=he.code)
                    logger.error(f"[GROQ PROVIDER] Slot {masked_key} invalid auth ({he.code}). Marking dead.")
                else:
                    return FederatedTaskResult(
                        task_id=request.task_id,
                        provider_domain=self.domain,
                        model_name=model,
                        status="FAILED",
                        content="",
                        execution_duration_ms=elapsed_ms,
                        error_message=f"HTTP {he.code}: {he.reason}",
                    )
            except Exception as e:
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                return FederatedTaskResult(
                    task_id=request.task_id,
                    provider_domain=self.domain,
                    model_name=model,
                    status="FAILED",
                    content="",
                    execution_duration_ms=elapsed_ms,
                    error_message=str(e),
                )

        return FederatedTaskResult(
            task_id=request.task_id,
            provider_domain=self.domain,
            model_name=model,
            status="FAILED",
            content="",
            execution_duration_ms=0.0,
            error_message="Groq key pool exhausted after all rotation attempts.",
        )
