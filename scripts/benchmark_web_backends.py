"""
scripts/benchmark_web_backends.py — Mesure réelle des backends Web fonctionnels.
"""
import asyncio
import os
import sys
import time

sys.path.insert(0, os.getcwd())

import httpx

from core.config import secrets_loader

secrets_loader.load(override=False)

from core.providers.jina_provider import JinaProvider
from core.providers.tavily_provider import TavilyProvider


async def test_duckduckgo():
    print("\n--- TEST: DuckDuckGo (via ddgs package) ---")
    try:
        from ddgs import DDGS
        start = time.perf_counter()
        results = list(DDGS().text("Python asyncio returncode", max_results=3))
        lat = (time.perf_counter() - start) * 1000.0
        print(f"  Status: FUNCTIONAL (latency: {lat:.1f}ms, results: {len(results)})")
        if results:
            print(f"  Sample: {results[0].get('title', '')} - {results[0].get('href', '')}")
        return True, lat, len(results)
    except Exception as e:
        print(f"  Status: FAILED ({e})")
        return False, 0.0, 0


async def test_tavily():
    print("\n--- TEST: Tavily Search ---")
    try:
        provider = TavilyProvider()
        start = time.perf_counter()
        res = await provider.search("Python asyncio returncode", max_results=3)
        lat = (time.perf_counter() - start) * 1000.0
        items = res.get("data", {}).get("results", [])
        print(f"  Status: FUNCTIONAL (latency: {lat:.1f}ms, results: {len(items)})")
        if items:
            print(f"  Sample: {items[0].get('title', '')} - {items[0].get('url', '')}")
        return True, lat, len(items)
    except Exception as e:
        print(f"  Status: FAILED ({e})")
        return False, 0.0, 0


async def test_jina_search():
    print("\n--- TEST: Jina Search (s.jina.ai) ---")
    try:
        provider = JinaProvider()
        start = time.perf_counter()
        res = await provider.search("Python asyncio returncode")
        lat = (time.perf_counter() - start) * 1000.0
        items = res.get("data", {}).get("results", [])
        print(f"  Status: FUNCTIONAL (latency: {lat:.1f}ms, results: {len(items)})")
        if items:
            print(f"  Sample: {items[0].get('title', '')} - {items[0].get('url', '')}")
        return True, lat, len(items)
    except Exception as e:
        print(f"  Status: FAILED ({e})")
        return False, 0.0, 0


async def test_jina_reader():
    print("\n--- TEST: Jina Reader Extract (r.jina.ai) ---")
    api_key = os.getenv("JINA_API_KEY")
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        target_url = "https://example.com"
        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"https://r.jina.ai/{target_url}", headers=headers)
            lat = (time.perf_counter() - start) * 1000.0
            if resp.status_code == 200:
                text = resp.text
                print(f"  Status: FUNCTIONAL (latency: {lat:.1f}ms, content length: {len(text)})")
                print(f"  Extract sample: {text[:120].strip()}")
                return True, lat, len(text)
            else:
                print(f"  Status: HTTP {resp.status_code}")
                return False, lat, 0
    except Exception as e:
        print(f"  Status: FAILED ({e})")
        return False, 0.0, 0


async def test_local_browser_headless():
    print("\n--- TEST: Local Headless Browser (Brave) ---")
    brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
    if not os.path.exists(brave_path):
        print("  Status: Brave binary not found")
        return False, 0.0, 0
    try:
        start = time.perf_counter()
        proc = await asyncio.create_subprocess_exec(
            brave_path,
            "--headless=new",
            "--dump-dom",
            "https://example.com",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10.0)
        lat = (time.perf_counter() - start) * 1000.0
        dom_text = stdout.decode("utf-8", errors="replace")
        print(f"  Status: FUNCTIONAL (latency: {lat:.1f}ms, dom length: {len(dom_text)})")
        print(f"  Sample DOM: {dom_text[:100].strip()}")
        return True, lat, len(dom_text)
    except Exception as e:
        print(f"  Status: FAILED ({e})")
        return False, 0.0, 0


async def main():
    print("=== E-ZZIO REAL WEB CAPABILITY BENCHMARK ===")
    await test_duckduckgo()
    await test_tavily()
    await test_jina_search()
    await test_jina_reader()
    await test_local_browser_headless()


if __name__ == "__main__":
    asyncio.run(main())
