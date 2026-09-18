"""E-ZZIO model scoring policies."""

from __future__ import annotations


def classify_tier(
    *,
    latency_ms: float,
    context_window: int | None,
    supports_json: bool,
    supports_tools: bool,
    supports_reasoning: bool,
) -> str:

    if supports_reasoning and (context_window or 0) >= 64_000:
        return "HEAVY"

    if latency_ms <= 900.0 and supports_json:
        return "FAST"

    if latency_ms <= 2500.0 or supports_tools:
        return "MID"

    return "HEAVY"


def calculate_score(
    *,
    latency_ms: float,
    supports_json: bool,
    supports_tools: bool,
    supports_reasoning: bool,
    context_window: int | None,
) -> float:

    score = 100.0
    score -= min(latency_ms / 100.0, 40.0)

    if supports_json:
        score += 10.0

    if supports_tools:
        score += 10.0

    if supports_reasoning:
        score += 15.0

    if (context_window or 0) >= 32_000:
        score += 5.0

    return round(
        max(0.0, min(100.0, score)),
        2,
    )
