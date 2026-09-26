"""
scripts/inventory_web.py — Diagnostic d'inventaire Web réel (sans afficher de secrets).
"""
import importlib.util
import os
import shutil
import socket

print("=== 1. PACKAGES PYTHON ===")
packages = [
    'duckduckgo_search', 'ddgs', 'tavily', 'brave', 'exa_py', 'firecrawl',
    'jina', 'playwright', 'selenium', 'browser_use', 'lightpanda',
    'requests', 'httpx', 'aiohttp', 'curl_cffi', 'bs4', 'trafilatura', 'pypdf', 'fitz'
]
for p in packages:
    spec = importlib.util.find_spec(p)
    status = "INSTALLED" if spec is not None else "NOT INSTALLED"
    print(f"  {p:20s}: {status}")

print("\n=== 2. LOCAL PORTS / SERVICES ===")
ports = {
    'SearXNG (8080)': ('127.0.0.1', 8080),
    'SearXNG (8888)': ('127.0.0.1', 8888),
    'Ollama (11434)': ('127.0.0.1', 11434),
    'Chrome CDP (9222)': ('127.0.0.1', 9222),
    'Edge CDP (9222)': ('127.0.0.1', 9222),
    'VoiceStudio (3900)': ('127.0.0.1', 3900),
    'Local ComfyUI (8188)': ('127.0.0.1', 8188)
}
for name, (host, port) in ports.items():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        res = s.connect_ex((host, port))
        is_open = (res == 0)
    except Exception:
        is_open = False
    finally:
        s.close()
    print(f"  {name:20s}: {'REACHABLE' if is_open else 'NOT LISTENING'}")

print("\n=== 3. BROWSERS INSTALLÉS ===")
browsers = {
    'Chrome': ['chrome', 'google-chrome', r'C:\Program Files\Google\Chrome\Application\chrome.exe', r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'],
    'Edge': ['msedge', r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe', r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'],
    'Brave': ['brave', r'C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe', r'C:\Users\enrik\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe'],
    'Chromium': ['chromium']
}
for bname, paths in browsers.items():
    found_p = None
    for p in paths:
        if shutil.which(p) or os.path.exists(p):
            found_p = p
            break
    print(f"  {bname:10s}: {'INSTALLED (' + str(found_p) + ')' if found_p else 'NOT FOUND'}")

print("\n=== 4. WEB SECRETS CONFIGURATION (BOOLEAN PRESENCE ONLY) ===")
import sys

sys.path.insert(0, os.getcwd())

from core.config import secrets_loader

env = secrets_loader.load(override=False)

secret_keys = [
    'TAVILY_API_KEY', 'BRAVE_API_KEY', 'EXA_API_KEY', 'FIRECRAWL_API_KEY',
    'JINA_API_KEY', 'PERPLEXITY_API_KEY', 'SEARXNG_URL', 'BROWSER_USE_API_KEY',
    'SERPER_API_KEY', 'GOOGLE_SEARCH_API_KEY', 'BING_SEARCH_API_KEY',
    'PARALLEL_API_KEY', 'KEENABLE_API_KEY'
]
for sk in secret_keys:
    val = os.environ.get(sk) or env.get(sk)
    has_val = bool(val and len(str(val).strip()) > 3)
    print(f"  {sk:22s}: {'PRESENT' if has_val else 'ABSENT'}")
