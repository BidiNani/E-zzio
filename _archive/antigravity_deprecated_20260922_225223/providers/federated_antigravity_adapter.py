from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from core.cognition.model_federation.antigravity_provider import (
    AntigravityFederatedProvider,
)
from core.cognition.model_federation.base_provider import (
    FederatedTaskRequest,
)
from providers.provider_response import ProviderResponse


class FederatedAntigravityAdapter:
    """
    Adaptateur du contrat fédéré Antigravity vers ProviderResponse.

    Contrat externe:
        async generate(...) -> ProviderResponse

    Contrat interne:
        FederatedTaskRequest -> FederatedTaskResult
    """

    def __init__(
        self,
        root_dir: Path = Path(r"G:\AI\E-zzio"),
    ) -> None:
        self.root_dir = root_dir
        self._provider: AntigravityFederatedProvider | None = None

    def _get_provider(self) -> AntigravityFederatedProvider:
        if self._provider is None:
            self._provider = AntigravityFederatedProvider(
                root_dir=self.root_dir
            )
        return self._provider

    @staticmethod
    def _result_to_response(result: Any) -> ProviderResponse:
        status = str(
            getattr(result, "status", "")
        ).upper()

        provider = "antigravity"

        model = str(
            getattr(result, "model_name", "")
            or "antigravity_agent_federated"
        )

        content = str(
            getattr(result, "content", "")
            or ""
        )

        error_message = getattr(
            result,
            "error_message",
            None,
        )

        if error_message is not None:
            error_message = str(error_message)

        metadata = {
            "federated": True,
            "task_id": getattr(result, "task_id", ""),
            "status": status,
            "cost_estimate_usd": getattr(
                result,
                "cost_estimate_usd",
                0.0,
            ),
            "timestamp_utc": getattr(
                result,
                "timestamp_utc",
                "",
            ),
        }

        structured_data = getattr(
            result,
            "structured_data",
            None,
        )

        if structured_data is not None:
            metadata["structured_data"] = structured_data

        raw_payload = getattr(
            result,
            "raw_response_payload",
            None,
        )

        if raw_payload is not None:
            metadata["raw_response_payload"] = raw_payload

        ok = status == "SUCCESS"

        if not ok and not error_message:
            error_message = (
                f"Federated Antigravity execution failed "
                f"with status={status or 'UNKNOWN'}"
            )

        return ProviderResponse(
            ok=ok,
            provider=provider,
            model=model,
            content=content,
            latency_ms=float(
                getattr(
                    result,
                    "execution_duration_ms",
                    0.0,
                ) or 0.0
            ),
            sources=[],
            error=None if ok else error_message,
            metadata=metadata,
        )

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        image_bytes: bytes | None = None,
        capability: str = "default",
    ) -> ProviderResponse:

        del image_bytes

        provider = self._get_provider()

        if not provider.is_available():
            return ProviderResponse(
                ok=False,
                provider="antigravity",
                model=model or "antigravity_agent_federated",
                error="Antigravity indisponible.",
                metadata={
                    "federated": True,
                    "failure_reason": "UNAVAILABLE",
                    "capability": capability,
                },
            )

        request = FederatedTaskRequest(
            task_id=f"EZZIO-AGY-{id(self):x}",
            task_type=capability or "default",
            prompt=prompt,
            max_tokens=2048,
            temperature=0.7,
            timeout_seconds=60,
            context_metadata={
                "model": model or "antigravity_agent_federated",
                "capability": capability,
                "allow_modifications": False,
            },
        )

        result = await asyncio.to_thread(
            provider.execute,
            request,
        )

        return self._result_to_response(result)
