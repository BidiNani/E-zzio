import asyncio
import os
import sys

sys.path.insert(0, os.getcwd())
from core.providers.ollama_provider import OllamaProvider


async def main():
    print("[*] Test d'inférence avec qwen3.5:9b (flux streaming actif)...")
    provider = OllamaProvider(model="qwen3.5:9b")
    res = await provider.search("Explique en 2 phrases simples ce qu'est un micro-noyau.")
    print(f"\n[OK] Provider : {res['provider']} ({res['model']})")
    print(f"[OK] Réponse  :\n{res['data']['text']}\n")


if __name__ == "__main__":
    asyncio.run(main())
