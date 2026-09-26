"""
core/capabilities/jev_decision.py — Isolated JEV Decision Capability Adapter.
Provides structured decision evaluation via typesafe/jev-1.13 and typesafe/jev-router.
STRICT FAIL-CLOSED CONTRACT: JEV is a CAPABILITY, never an AUTHORITY.
All errors or missing keys return UNKNOWN / fallback=True. Never defaults to ALLOW/SUCCESS.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

from core.secrets import get_api_key

logger = logging.getLogger("JevDecisionCapability")

JEV_1_13_MODEL = "typesafe/jev-1.13"
JEV_ROUTER_MODEL = "typesafe/jev-router"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Cost rates per 1M tokens (USD)
JEV_1_13_INPUT_COST_PER_1M = 0.042
JEV_1_13_OUTPUT_COST_PER_1M = 0.0
JEV_ROUTER_INPUT_COST_PER_1M = 0.0
JEV_ROUTER_OUTPUT_COST_PER_1M = 0.0


@dataclass
class JevDecisionResult:
    decision: str
    confidence: float
    reason: str
    model_used: str
    latency_ms: float
    tokens_used: int
    estimated_cost: float
    schema_valid: bool
    fallback: bool
    raw_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "confidence": self.confidence,
            "reason": self.reason,
            "model_used": self.model_used,
            "latency_ms": self.latency_ms,
            "tokens_used": self.tokens_used,
            "estimated_cost": self.estimated_cost,
            "schema_valid": self.schema_valid,
            "fallback": self.fallback,
            "raw_error": self.raw_error,
        }


class JevDecisionCapability:
    """Adaptateur de capacité décisionnelle isolé pour typesafe/jev-1.13 et typesafe/jev-router.
    N'exécute aucune politique et ne possède aucune autorité kernel.
    """

    def __init__(self, api_key: str | None = None, timeout: float = 5.0):
        self.api_key = api_key or get_api_key("OPENROUTER_API_KEY")
        self.timeout = timeout

    async def evaluate_decision(
        self,
        prompt: str,
        possible_decisions: list[str],
        context: dict[str, Any] | None = None,
        model: str = JEV_1_13_MODEL,
        mock_response: dict[str, Any] | None = None,
    ) -> JevDecisionResult:
        """Évalue une décision typée avec le contrat strict Fail-Closed."""
        start_time = time.perf_counter()

        # En mode offline/mock (tests déterministes)
        if mock_response is not None:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return JevDecisionResult(
                decision=mock_response.get("decision", "UNKNOWN"),
                confidence=float(mock_response.get("confidence", 0.0)),
                reason=mock_response.get("reason", "Mock response"),
                model_used=model,
                latency_ms=latency_ms,
                tokens_used=mock_response.get("tokens_used", 50),
                estimated_cost=self._calc_cost(model, mock_response.get("tokens_used", 50)),
                schema_valid=mock_response.get("schema_valid", True),
                fallback=mock_response.get("fallback", False),
            )

        if not self.api_key:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return JevDecisionResult(
                decision="UNKNOWN",
                confidence=0.0,
                reason="OPENROUTER_API_KEY missing - fail-closed fallback",
                model_used=model,
                latency_ms=latency_ms,
                tokens_used=0,
                estimated_cost=0.0,
                schema_valid=False,
                fallback=True,
                raw_error="NO_API_KEY",
            )

        system_instruction = (
            f"You are an isolated classification capability. "
            f"Evaluate the prompt and context and choose EXACTLY one decision from {possible_decisions}. "
            f"Respond ONLY in valid JSON with fields: 'decision' (str), 'confidence' (float 0.0-1.0), 'reason' (str)."
        )

        user_content = json.dumps({"prompt": prompt, "context": context or {}}, ensure_ascii=False)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ezzio/ezzio-core",
            "X-Title": "E-ZZIO Decision Intelligence Benchmark",
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
            "max_tokens": 150,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(OPENROUTER_API_URL, json=payload, headers=headers)
                latency_ms = (time.perf_counter() - start_time) * 1000

                if res.status_code != 200:
                    return JevDecisionResult(
                        decision="UNKNOWN",
                        confidence=0.0,
                        reason=f"HTTP {res.status_code}",
                        model_used=model,
                        latency_ms=latency_ms,
                        tokens_used=0,
                        estimated_cost=0.0,
                        schema_valid=False,
                        fallback=True,
                        raw_error=res.text[:200],
                    )

                resp_data = res.json()
                usage = resp_data.get("usage", {})
                tokens = usage.get("total_tokens", 0) or usage.get("prompt_tokens", 0)

                choice_content = resp_data["choices"][0]["message"]["content"]
                parsed = json.loads(choice_content)

                raw_dec = str(parsed.get("decision", "UNKNOWN")).upper()
                confidence = float(parsed.get("confidence", 0.0))
                reason = str(parsed.get("reason", ""))

                if raw_dec not in possible_decisions:
                    return JevDecisionResult(
                        decision="UNKNOWN",
                        confidence=0.0,
                        reason=f"Invalid decision returned: {raw_dec}",
                        model_used=model,
                        latency_ms=latency_ms,
                        tokens_used=tokens,
                        estimated_cost=self._calc_cost(model, tokens),
                        schema_valid=False,
                        fallback=True,
                    )

                return JevDecisionResult(
                    decision=raw_dec,
                    confidence=confidence,
                    reason=reason,
                    model_used=model,
                    latency_ms=latency_ms,
                    tokens_used=tokens,
                    estimated_cost=self._calc_cost(model, tokens),
                    schema_valid=True,
                    fallback=False,
                )

        except Exception as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.warning("Jev capability exception: %s", exc)
            return JevDecisionResult(
                decision="UNKNOWN",
                confidence=0.0,
                reason=f"Exception: {str(exc)}",
                model_used=model,
                latency_ms=latency_ms,
                tokens_used=0,
                estimated_cost=0.0,
                schema_valid=False,
                fallback=True,
                raw_error=str(exc),
            )

    def _calc_cost(self, model: str, tokens: int) -> float:
        if "jev-router" in model:
            return 0.0
        return (tokens / 1_000_000.0) * JEV_1_13_INPUT_COST_PER_1M


@dataclass
class JevShadowRecord:
    timestamp: float
    decision_id: str
    decision_type: str
    canonical_decision: str
    jev_decision: str
    jev_confidence: float
    latency_ms: float
    api_success: bool
    fallback: bool
    match: bool
    model_used: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "decision_id": self.decision_id,
            "decision_type": self.decision_type,
            "canonical_decision": self.canonical_decision,
            "jev_decision": self.jev_decision,
            "jev_confidence": self.jev_confidence,
            "latency_ms": self.latency_ms,
            "api_success": self.api_success,
            "fallback": self.fallback,
            "match": self.match,
            "model_used": self.model_used,
        }


class JevShadowEvaluator:
    """Évaluateur en Shadow Mode purement observatif pour JEV 1.13 et JEV Router.
    N'altère pas le chemin nominal et n'a aucune autorité opérationnelle.
    """

    def __init__(self, capability: JevDecisionCapability | None = None):
        self.capability = capability or JevDecisionCapability()
        self.records: list[JevShadowRecord] = []

    async def record_shadow_decision(
        self,
        decision_id: str,
        decision_type: str,
        prompt: str,
        possible_decisions: list[str],
        canonical_decision: str,
        model: str = JEV_1_13_MODEL,
        mock_response: dict[str, Any] | None = None,
    ) -> JevShadowRecord:
        jev_res = await self.capability.evaluate_decision(
            prompt=prompt,
            possible_decisions=possible_decisions,
            model=model,
            mock_response=mock_response,
        )

        match = (jev_res.decision == canonical_decision)
        rec = JevShadowRecord(
            timestamp=time.time(),
            decision_id=decision_id,
            decision_type=decision_type,
            canonical_decision=canonical_decision,
            jev_decision=jev_res.decision,
            jev_confidence=jev_res.confidence,
            latency_ms=jev_res.latency_ms,
            api_success=jev_res.schema_valid and not jev_res.fallback,
            fallback=jev_res.fallback,
            match=match,
            model_used=model,
        )
        self.records.append(rec)
        return rec

    def compute_metrics(self) -> dict[str, Any]:
        if not self.records:
            return {"total": 0}

        total = len(self.records)
        matches = sum(1 for r in self.records if r.match)
        successful_api = sum(1 for r in self.records if r.api_success)
        fallbacks = sum(1 for r in self.records if r.fallback)

        high_conf_records = [r for r in self.records if r.jev_confidence >= 0.85]
        high_conf_total = len(high_conf_records)
        high_conf_matches = sum(1 for r in high_conf_records if r.match)

        latencies = [r.latency_ms for r in self.records]
        latencies.sort()
        p50 = latencies[int(len(latencies) * 0.5)] if latencies else 0.0
        p95 = latencies[int(len(latencies) * 0.95) - 1] if latencies else 0.0

        return {
            "total": total,
            "accuracy": (matches / total) * 100.0 if total > 0 else 0.0,
            "coverage": (successful_api / total) * 100.0 if total > 0 else 0.0,
            "fallback_rate": (fallbacks / total) * 100.0 if total > 0 else 0.0,
            "high_confidence_count": high_conf_total,
            "high_confidence_accuracy": (high_conf_matches / high_conf_total * 100.0) if high_conf_total > 0 else 0.0,
            "p50_latency_ms": p50,
            "p95_latency_ms": p95,
        }
