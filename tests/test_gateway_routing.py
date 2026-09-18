#!/usr/bin/env python3
"""Validation des routes ezzio-fast, ezzio-mid et ezzio-heavy."""

import asyncio
import time

from openai import AsyncOpenAI

GATEWAY_URL = "http://127.0.0.1:4000/v1"
MASTER_KEY = "sk-ezzio-local-gateway-token"

CLIENT = AsyncOpenAI(base_url=GATEWAY_URL, api_key=MASTER_KEY)
TIERS = ["ezzio-fast", "ezzio-mid", "ezzio-heavy"]


async def verify_tier(tier: str) -> dict[str, str | float | bool]:
    start_time = time.perf_counter()
    try:
        response = await CLIENT.chat.completions.create(
            model=tier,
            messages=[{"role": "user", "content": "Ping. Réponds uniquement par le mot OK."}],
            max_tokens=5,
            timeout=15.0,
        )
        latency = (time.perf_counter() - start_time) * 1000.0
        content = response.choices[0].message.content or ""
        provider_used = getattr(response, "model", "inconnu")
        return {
            "tier": tier,
            "success": "OK" in content,
            "provider": provider_used,
            "latency_ms": round(latency, 2),
        }
    except Exception as exc:
        latency = (time.perf_counter() - start_time) * 1000.0
        return {
            "tier": tier,
            "success": False,
            "error": str(exc),
            "latency_ms": round(latency, 2),
        }


async def main() -> None:
    print("--- Test de connectivité Gateway E-zzio ---")
    results = await asyncio.gather(*(verify_tier(t) for t in TIERS))
    for res in results:
        status = "VALIDE" if res.get("success") else "ECHEC"
        print(f"[{status}] {res['tier']} -> {res.get('provider', 'N/A')} ({res['latency_ms']} ms)")
        if not res.get("success"):
            print(f"       Détail : {res.get('error')}")


if __name__ == "__main__":
    asyncio.run(main())
