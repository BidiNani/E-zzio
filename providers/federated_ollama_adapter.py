from __future__ import annotations

from pathlib import Path
from typing import Optional

from providers.provider_response import ProviderResponse
from providers.ollama_provider import OllamaProvider
from core.cognition.model_federation.base_provider import (
    FederatedTaskResult,
    ProviderDomain,
)


class FederatedOllamaAdapter:

    def __init__(
        self,
        root_dir: Path = Path(r"G:\AI\E-zzio"),
    ) -> None:
        self.root_dir = root_dir
        self._provider: Optional[OllamaProvider] = None

    def _get_provider(self) -> OllamaProvider:
        if self._provider is None:
            self._provider = OllamaProvider()
        return self._provider

    @staticmethod
    def _result_to_response(result: FederatedTaskResult) -> ProviderResponse:
        status = str(result.status).upper()
        ok = status == "SUCCESS"

        error = result.error_message

        if not ok and not error:
            error = (
                f"Federated Ollama execution failed: "
                f"{status or 'UNKNOWN'}"
            )

        metadata = {
            "federated": True,
            "task_id": result.task_id,
            "status": status,
            "cost_estimate_usd": result.cost_estimate_usd,
            "timestamp_utc": result.timestamp_utc,
        }

        if result.structured_data is not None:
            metadata["structured_data"] = result.structured_data

        if result.raw_response_payload is not None:
            metadata["raw_response_payload"] = result.raw_response_payload

        return ProviderResponse(
            ok=ok,
            provider="ollama",
            model=result.model_name,
            content=result.content,
            latency_ms=float(result.execution_duration_ms or 0.0),
            sources=[],
            error=None if ok else error,
            metadata=metadata,
        )

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        capability: str = "default",
    ) -> ProviderResponse:

        provider = self._get_provider()

        legacy_response = await provider.generate(
            prompt=prompt,
            model=model,
            image_bytes=image_bytes,
            capability=capability,
        )

        result = FederatedTaskResult(
            task_id=f"EZZIO-OLLAMA-{id(self):x}",
            provider_domain=ProviderDomain.LOCAL_OLLAMA,
            model_name=legacy_response.model,
            status="SUCCESS" if legacy_response.ok else "FAILED",
            content=legacy_response.content,
            structured_data=None,
            error_message=legacy_response.error,
            raw_response_payload=None,
            execution_duration_ms=legacy_response.latency_ms,
            cost_estimate_usd=0.0,
        )

        return self._result_to_response(result)
