"""
scripts/measure_browser_warmup.py — Mesure de démarrage à froid vs chaud du navigateur local Brave.
"""
import asyncio
import os
import sys
import time

sys.path.insert(0, os.getcwd())

from core.capabilities.web_provider import find_local_browser


async def measure_cold_launch(url: str = "https://example.com"):
    browser_path, browser_name = find_local_browser()
    if not browser_path:
        print("  Browser path absent")
        return 0.0, 0

    t0 = time.perf_counter()
    proc = await asyncio.create_subprocess_exec(
        browser_path,
        "--headless=new",
        "--dump-dom",
        url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    lat = (time.perf_counter() - t0) * 1000.0
    return lat, len(stdout)


async def main():
    print("=== MEASURING LOCAL BROWSER COLD LAUNCH LATENCY ===")
    latencies = []
    for i in range(3):
        lat, length = await measure_cold_launch("https://example.com")
        latencies.append(lat)
        print(f"  Run {i+1}: {lat:.1f} ms (DOM length: {length})")

    avg_cold = sum(latencies) / len(latencies) if latencies else 0.0
    print(f"\n  Average Cold Launch Latency: {avg_cold:.1f} ms")
    print("  Local HTTP Scraper Latency (Reference): ~60.0 ms")
    print("  Jina Reader API Latency (Reference): ~480.0 ms")

if __name__ == "__main__":
    asyncio.run(main())
