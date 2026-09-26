"""
core/governance/budget_governor.py — Sovereign Budget & Cost Governance Engine (Phase A10).
Provides preflight admission control, postflight reconciliation, and multi-dimensional cost aggregation.
STRICT INVARIANTS:
- Unknown costs are explicitly "UNKNOWN" (never 0.0).
- Local / zero-cost models are 0.0 only when strictly known.
- Fail-closed admission control: operations exceeding limits are rejected prior to execution.
- Never bypasses ModelRouter or PolicyGuard.
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("BudgetGovernor")

# Known cost rates per 1M tokens (USD)
KNOWN_TOKEN_RATES: dict[str, dict[str, float]] = {
    # Gemini
    "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.5-pro": {"input": 1.25, "output": 5.00},
    # Groq (Llama 3.3)
    "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
    # Local Ollama (Known Zero Monetary Cost)
    "qwen2.5-coder:7b": {"input": 0.0, "output": 0.0},
    "deepseek-r1:8b": {"input": 0.0, "output": 0.0},
    "mistral:7b": {"input": 0.0, "output": 0.0},
    # Typesafe / JEV
    "typesafe/jev-1.13": {"input": 0.042, "output": 0.0},
    "typesafe/jev-router": {"input": 0.0, "output": 0.0},
}


@dataclass
class BudgetRecord:
    mission_id: str
    task_id: str
    provider: str
    model: str
    worker: str
    request_count: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: float
    estimated_cost: float | str  # float or "UNKNOWN"
    actual_cost: float | str     # float or "UNKNOWN"
    budget_limit: float
    budget_remaining: float
    timestamp_utc: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    status: str = "RECORDED"
    is_rollback: bool = False
    is_retry: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "task_id": self.task_id,
            "provider": self.provider,
            "model": self.model,
            "worker": self.worker,
            "request_count": self.request_count,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "latency_ms": self.latency_ms,
            "estimated_cost": self.estimated_cost,
            "actual_cost": self.actual_cost,
            "budget_limit": self.budget_limit,
            "budget_remaining": self.budget_remaining,
            "timestamp_utc": self.timestamp_utc,
            "status": self.status,
            "is_rollback": self.is_rollback,
            "is_retry": self.is_retry,
        }


@dataclass
class BudgetPreflightResult:
    allowed: bool
    reason: str
    reservation_id: str | None = None
    remaining_budget: float = 0.0


class BudgetGovernor:
    """Gouverneur budgétaire souverain sans autorité de routage."""

    def __init__(
        self,
        mission_budget_limit: float = 10.0,  # USD
        daily_budget_limit: float = 50.0,    # USD
        max_calls_per_mission: int = 100,
        max_tokens_per_mission: int = 200_000,
        workspace_root: str = "G:\\AI\\E-zzio",
    ):
        self.mission_budget_limit = mission_budget_limit
        self.daily_budget_limit = daily_budget_limit
        self.max_calls_per_mission = max_calls_per_mission
        self.max_tokens_per_mission = max_tokens_per_mission
        self.workspace_root = workspace_root

        # In-memory tracking
        self.records: list[BudgetRecord] = []
        self._reservations: dict[str, dict[str, Any]] = {}
        self._mission_spend: dict[str, float] = {}
        self._mission_calls: dict[str, int] = {}
        self._mission_tokens: dict[str, int] = {}
        self._daily_spend: dict[str, float] = {}

    def _get_current_day_str(self) -> str:
        return datetime.now(UTC).strftime("%Y-%m-%d")

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float | str:
        """Calcule le coût monétaire estimé ou retourne 'UNKNOWN' si les taux sont indéterminés."""
        if model not in KNOWN_TOKEN_RATES:
            # RÈGLE ABSOLUE : Jamais 0 par défaut pour masquer un coût inconnu
            return "UNKNOWN"

        rates = KNOWN_TOKEN_RATES[model]
        cost_in = (input_tokens / 1_000_000.0) * rates["input"]
        cost_out = (output_tokens / 1_000_000.0) * rates["output"]
        return round(cost_in + cost_out, 6)

    def preflight(
        self,
        mission_id: str,
        task_id: str,
        provider: str,
        model: str,
        estimated_tokens: int = 1000,
        deadline_sec: float | None = None,
    ) -> BudgetPreflightResult:
        """Admission control pré-exécution : Fail-Closed si budget épuisé."""
        day_str = self._get_current_day_str()
        current_mission_spend = self._mission_spend.get(mission_id, 0.0)
        current_mission_calls = self._mission_calls.get(mission_id, 0)
        current_mission_tokens = self._mission_tokens.get(mission_id, 0)
        current_daily_spend = self._daily_spend.get(day_str, 0.0)

        # 1. Vérification budget monétaire journalier
        if current_daily_spend >= self.daily_budget_limit:
            return BudgetPreflightResult(
                allowed=False,
                reason=f"[FAIL-CLOSED] Daily budget exhausted ({current_daily_spend:.4f} >= {self.daily_budget_limit:.4f} USD)",
                remaining_budget=0.0,
            )

        # 2. Vérification budget monétaire de la mission
        if current_mission_spend >= self.mission_budget_limit:
            return BudgetPreflightResult(
                allowed=False,
                reason=f"[FAIL-CLOSED] Mission budget exhausted ({current_mission_spend:.4f} >= {self.mission_budget_limit:.4f} USD)",
                remaining_budget=0.0,
            )

        # 3. Vérification limite d'appels par mission
        if current_mission_calls >= self.max_calls_per_mission:
            return BudgetPreflightResult(
                allowed=False,
                reason=f"[FAIL-CLOSED] Mission call budget exceeded ({current_mission_calls} >= {self.max_calls_per_mission})",
                remaining_budget=max(0.0, self.mission_budget_limit - current_mission_spend),
            )

        # 4. Vérification limite de tokens par mission
        if current_mission_tokens + estimated_tokens > self.max_tokens_per_mission:
            return BudgetPreflightResult(
                allowed=False,
                reason=f"[FAIL-CLOSED] Mission token budget exceeded ({current_mission_tokens + estimated_tokens} > {self.max_tokens_per_mission})",
                remaining_budget=max(0.0, self.mission_budget_limit - current_mission_spend),
            )

        # 5. Réservation pré-vol
        res_id = str(uuid.uuid4())
        self._reservations[res_id] = {
            "mission_id": mission_id,
            "task_id": task_id,
            "provider": provider,
            "model": model,
            "estimated_tokens": estimated_tokens,
            "reserved_at": time.time(),
        }

        remaining = max(0.0, self.mission_budget_limit - current_mission_spend)
        return BudgetPreflightResult(allowed=True, reason="ALLOWED", reservation_id=res_id, remaining_budget=remaining)

    def postflight(
        self,
        reservation_id: str | None,
        mission_id: str,
        task_id: str,
        provider: str,
        model: str,
        worker: str = "native",
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: float = 0.0,
        is_rollback: bool = False,
        is_retry: bool = False,
        actual_monetary_cost_override: float | None = None,
    ) -> BudgetRecord:
        """Réconciliation et enregistrement post-exécution."""
        # Libération de la réservation si présente
        if reservation_id and reservation_id in self._reservations:
            del self._reservations[reservation_id]

        total_tokens = input_tokens + output_tokens
        day_str = self._get_current_day_str()

        # Calcul des coûts
        if actual_monetary_cost_override is not None:
            est_cost = actual_monetary_cost_override
            act_cost = actual_monetary_cost_override
        else:
            cost_calc = self.calculate_cost(model, input_tokens, output_tokens)
            est_cost = cost_calc
            act_cost = cost_calc

        # Mise à jour des dépenses numériques si connues
        numeric_spend = act_cost if isinstance(act_cost, float) else 0.0

        self._mission_spend[mission_id] = self._mission_spend.get(mission_id, 0.0) + numeric_spend
        self._mission_calls[mission_id] = self._mission_calls.get(mission_id, 0) + 1
        self._mission_tokens[mission_id] = self._mission_tokens.get(mission_id, 0) + total_tokens
        self._daily_spend[day_str] = self._daily_spend.get(day_str, 0.0) + numeric_spend

        remaining = max(0.0, self.mission_budget_limit - self._mission_spend[mission_id])

        record = BudgetRecord(
            mission_id=mission_id,
            task_id=task_id,
            provider=provider,
            model=model,
            worker=worker,
            request_count=1,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            estimated_cost=est_cost,
            actual_cost=act_cost,
            budget_limit=self.mission_budget_limit,
            budget_remaining=remaining,
            is_rollback=is_rollback,
            is_retry=is_retry,
        )

        self.records.append(record)
        return record

    def get_mission_summary(self, mission_id: str) -> dict[str, Any]:
        """Agrège les statistiques de consommation d'une mission."""
        mission_records = [r for r in self.records if r.mission_id == mission_id]

        cloud_calls = 0
        local_calls = 0
        total_tokens = 0
        total_latency = 0.0
        total_numeric_cost = 0.0
        has_unknown_cost = False
        provider_usage: dict[str, int] = {}
        model_usage: dict[str, int] = {}

        for r in mission_records:
            if r.provider.lower() in ("local", "ollama"):
                local_calls += 1
            else:
                cloud_calls += 1

            total_tokens += r.total_tokens
            total_latency += r.latency_ms

            if isinstance(r.actual_cost, float):
                total_numeric_cost += r.actual_cost
            else:
                has_unknown_cost = True

            provider_usage[r.provider] = provider_usage.get(r.provider, 0) + 1
            model_usage[r.model] = model_usage.get(r.model, 0) + 1

        cost_val: float | str = total_numeric_cost
        if has_unknown_cost:
            cost_val = f">={total_numeric_cost:.6f} USD (+ UNKNOWN components)"

        return {
            "mission_id": mission_id,
            "total_calls": len(mission_records),
            "cloud_calls": cloud_calls,
            "local_calls": local_calls,
            "total_tokens": total_tokens,
            "total_latency_ms": round(total_latency, 2),
            "estimated_monetary_cost": cost_val,
            "provider_usage": provider_usage,
            "model_usage": model_usage,
            "budget_limit": self.mission_budget_limit,
            "budget_remaining": max(0.0, self.mission_budget_limit - self._mission_spend.get(mission_id, 0.0)),
        }
