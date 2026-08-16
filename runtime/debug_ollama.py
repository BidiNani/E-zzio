import asyncio
import sys
import os
import traceback

# Ajout de la racine du projet au chemin d'importation Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.providers.ollama_provider import OllamaProvider

async def main():
    print("[*] Instanciation d'OllamaProvider avec qwen3.5:9b...")
    provider = OllamaProvider(model="qwen3.5:9b")
    
    try:
        print("[*] Envoi de la requête de test (timeout 120s pour le cold start)...")
        res = await provider.search("Explique l'architecture micro-noyau", timeout=120.0)
        print("[[OK]] Inférence réussie :")
        print(res.get("data", {}).get("text", ""))
    except Exception as e:
        print("\n[[ERREUR CAPTURÉE]]")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
