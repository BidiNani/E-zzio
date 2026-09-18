"""E-ZZIO model qualification gate — FREE_ONLY / FAIL-CLOSED."""

from __future__ import annotations

from typing import Any

from .free_only import annotate_free_status
from .policies import policy_allows
from .probes import exact_text_probe, openai_compatible_probe


class QualificationGate:
    FAST_MAX_LATENCY_MS = 1000.0
    MID_MAX_LATENCY_MS = 5000.0
    MIN_SCORE = 70.0

    async def qualify_openai_compatible(
        self,
        *,
        provider: str,
        model: dict[str, Any],
        api_key: str,
        endpoint: str,
    ) -> dict[str, Any]:

        # DEFENSE-IN-DEPTH RECHECK GUARD
        if not policy_allows(model):
            return {
                "provider": provider,
                "model_id": model.get("model_id") or model.get("id") or "unknown",
                "qualified": False,
                "tier": "UNQUALIFIED",
                "score": 0.0,
                "latency_ms": 0.0,
                "http_status": None,
                "failures": ["free_only_recheck_violation"],
                "error_detail": "Blocked by QualificationGate recheck guard",
                "structured_json": False,
                "exact_contract_match": False,
                "exact_text_match": False,
                "free_only": False,
                "free_status": model.get("free_status", "UNKNOWN"),
                "qualification_policy": "FREE_ONLY",
                "capabilities": {
                    "chat": bool(model.get("supports_chat")),
                    "json": bool(model.get("supports_json")),
                    "reasoning": bool(model.get("supports_reasoning", False)),
                },
            }

        model = annotate_free_status(model)

        probe = await openai_compatible_probe(
            endpoint=endpoint,
            api_key=api_key,
            model_id=str(model["model_id"]),
        )

        text_probe = await exact_text_probe(
            endpoint=endpoint,
            api_key=api_key,
            model_id=model["model_id"],
        )

        score = 0.0

        if probe.get("success") is True:
            score += 25.0

        if probe.get("content_available") is True:
            score += 15.0

        if probe.get("structured_json") is True:
            score += 15.0

        if probe.get("exact_contract_match") is True:
            score += 25.0

        if text_probe.get("success") is True:
            score += 10.0

        if text_probe.get("exact_text_match") is True:
            score += 10.0

        latency_value = probe.get("latency_ms")

        try:
            latency_ms = float(latency_value)
        except (TypeError, ValueError):
            latency_ms = 999999.0

        model_id_lower = str(
            model.get("model_id", "")
        ).lower()

        supports_reasoning = bool(
            model.get("supports_reasoning", False)
        )

        qualified = bool(
            probe.get("success") is True
            and probe.get("exact_contract_match") is True
            and text_probe.get("success") is True
            and text_probe.get("exact_text_match") is True
            and score >= self.MIN_SCORE
        )

        if not qualified:
            tier = "UNQUALIFIED"

        elif supports_reasoning:
            tier = (
                "MID"
                if latency_ms <= self.MID_MAX_LATENCY_MS
                else "HEAVY"
            )

        elif (
            "-mini" in model_id_lower
            or "instant" in model_id_lower
            or latency_ms <= self.FAST_MAX_LATENCY_MS
        ):
            tier = "FAST"

        elif latency_ms <= self.MID_MAX_LATENCY_MS:
            tier = "MID"

        else:
            tier = "HEAVY"

        failures: list[str] = []

        if not probe.get("success"):
            failures.append("probe_http_failure")

        if not probe.get("content_available"):
            failures.append("empty_content")

        if not probe.get("structured_json"):
            failures.append("structured_json_failure")

        if not probe.get("exact_contract_match"):
            failures.append("output_contract_violation")

        if not text_probe.get("exact_text_match"):
            failures.append("exact_text_contract_violation")

        if probe.get("error_detail"):
            failures.append(
                str(probe["error_detail"])[:300]
            )

        return {
            "provider": provider,
            "model_id": model["model_id"],
            "qualified": qualified,
            "tier": tier,
            "score": round(score, 2),
            "latency_ms": round(latency_ms, 2),
            "http_status": probe.get("http_status"),
            "failures": failures,
            "error_detail": probe.get("error_detail"),
            "structured_json": bool(
                probe.get("structured_json")
            ),
            "exact_contract_match": bool(
                probe.get("exact_contract_match")
            ),
            "exact_text_match": bool(
                text_probe.get("exact_text_match")
            ),
            "text_probe_latency_ms": text_probe.get("latency_ms"),
            "free_only": True,
            "free_status": "FREE",
            "qualification_policy": "FREE_ONLY",
            "capabilities": {
                "chat": bool(
                    model.get("supports_chat")
                ),
                "json": bool(
                    model.get("supports_json")
                ),
                "reasoning": supports_reasoning,
            },
        }
