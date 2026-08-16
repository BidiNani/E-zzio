import asyncio
import os
from core.providers.ollama_provider import OllamaProvider
from core.secrets import load_secrets

async def test_qwen_load():
    load_secrets()
    # Forcer la variable d'environnement pour le test immédiat
    os.environ["OLLAMA_MODEL"] = "qwen3.5:9b"
    
    print("[*] Initialisation de l'instance Ollama avec qwen3.5:9b...")
    provider = OllamaProvider(model="qwen3.5:9b")
    
    print("[*] Envoi de la requête de test (chargement à froid possible, timeout 120s)...")
    try:
        res = await provider.search("Donne un résumé technique d'un système micro-noyau en une phrase.", timeout=120.0)
        print(f"[OK] Succès ! Provider : {res.get('provider')}")
        print(f"[OK] Modèle   : {res.get('model')}")
        print(f"[OK] Réponse  :\n{res.get('data', {}).get('text')}")
    except Exception as e:
        print(f"[ERREUR] Échec de l'inférence locale : {e}")

if __name__ == "__main__":
    asyncio.run(test_qwen_load())
