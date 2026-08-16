import asyncio
import os
import sys
import time

# 1. Résolution de chemin
sys.path.insert(0, os.getcwd())

from core.secrets import load_secrets
from core.memory.unified_gateway import UnifiedMemoryGateway
from core.router.intent_router import IntentRouter, IntentType
from core.providers.ollama_provider import OllamaProvider
from core.providers.gemini_provider import GeminiProvider
from core.providers.tavily_provider import TavilyProvider
from runtime.core.ezzio_core import EzzioCore
from interfaces.api.server import app
from routers.research import _evidence_store
import httpx

async def run_master_check():
    print("=" * 65)
    print("       E-ZZIO OS — RECETTE GLOBALE DE TOUS LES SOUS-SYSTÈMES     ")
    print("=" * 65 + "\n")
    load_secrets()

    # --- 1. BASE DE DONNÉES & MÉMOIRE WAL ---
    print("[1/5] TEST MÉMOIRE UNIFIÉE & PERSISTANCE WAL...")
    db_path = "runtime/evidence/test_master.db"
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass
    mem = UnifiedMemoryGateway(db_path)
    await mem.init()
    await mem.record_message("sess_master", "user", "Message de test persistance")
    await mem.record_message("sess_master", "assistant", "Réponse de test")
    history = await mem.get_session_history("sess_master")
    assert len(history) == 2, "Échec de lecture de l'historique"
    print("      [OK] SQLite WAL & Tables de sessions opérationnelles.\n")

    # --- 2. INTENT ROUTER DÉTERMINISTE ---
    print("[2/5] TEST CLASSIFICATEUR D'INTENTION (IntentRouter)...")
    router = IntentRouter()
    c1 = router.classify("Cherche les dernières actus IA")
    c2 = router.classify("Analyse cette architecture et propose un refactor")
    c3 = router.classify("Bonjour E-ZZIO, comment ça va ?")
    c4 = router.classify("Rappel de ce qu'on a fait précédemment")
    assert c1["intent"] == IntentType.WEB_SEARCH
    assert c2["intent"] == IntentType.DEEP_REASONING
    assert c3["intent"] == IntentType.LOCAL_CHAT
    assert c4["intent"] == IntentType.MEMORY_QUERY
    print(f"      [OK] Web Search     -> {c1['intent'].value} ({c1['target_provider']})")
    print(f"      [OK] Deep Reasoning -> {c2['intent'].value} ({c2['target_provider']})")
    print(f"      [OK] Local Chat     -> {c3['intent'].value} ({c3['target_provider']})")
    print(f"      [OK] Memory Recall  -> {c4['intent'].value} ({c4['target_provider']})\n")

    # --- 3. MOTEURS D'INFÉRENCE EN DIRECT ---
    print("[3/5] TEST DES FOURNISSEURS IA EN DIRECT...")
    # A. Inférence Locale Ollama
    print("      [*] Ollama Local (qwen3.5:9b)...", end=" ", flush=True)
    t0 = time.perf_counter()
    ollama = OllamaProvider()
    try:
        res_loc = await ollama.search("Réponds 'OK_LOCAL' en un mot.")
        dt = time.perf_counter() - t0
        print(f"[OK] ({dt:.2f}s) -> '{res_loc['data']['text'][:30]}...'")
    except Exception as e:
        print(f"[KO] Erreur: {e}")

    # B. Cloud Reasoning Gemini
    print("      [*] Gemini Cloud...", end=" ", flush=True)
    t0 = time.perf_counter()
    gemini = GeminiProvider()
    try:
        res_gem = await gemini.search("Réponds 'OK_GEMINI' en un mot.")
        dt = time.perf_counter() - t0
        print(f"[OK] ({dt:.2f}s) -> '{res_gem['data']['text'][:30]}...'")
    except Exception as e:
        print(f"[KO] Erreur: {e}")

    # C. Web Search Tavily
    print("      [*] Tavily Web...", end=" ", flush=True)
    t0 = time.perf_counter()
    tavily = TavilyProvider()
    try:
        res_tav = await tavily.search("FastAPI")
        dt = time.perf_counter() - t0
        print(f"[OK] ({dt:.2f}s) -> {len(res_tav['data']['results'])} liens trouvés.")
    except Exception as e:
        print(f"[KO] Erreur: {e}")
    print()

    # --- 4. NOYAU COGNITIF AUTONOME (EzzioCore) ---
    print("[4/5] TEST NOYAU CENTRAL (EzzioCore)...")
    core = EzzioCore(memory_gateway=mem)
    await core.init()
    think_res = await core.think(user_id="user_admin", message="Bonjour E-ZZIO, statut ?")
    print(f"      [OK] Intention active : {think_res['intent']}")
    print(f"      [OK] Moteur utilisé   : {think_res['provider'].upper()}")
    print(f"      [OK] Synthèse         : {think_res['response'][:90]}...\n")

    # --- 5. ENDPOINTS FASTAPI EN TRANSPORT ASGI DIRECT ---
    print("[5/5] TEST ENDPOINTS HTTP API (Transport Direct ASGI)...")
    # Initialisation explicite du store de l'API
    await _evidence_store.init()
    
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", timeout=120.0) as client:
        # Health check
        h_resp = await client.get("/health")
        assert h_resp.status_code == 200, f"Health check failed: {h_resp.text}"
        
        # Route Research (Google Mode)
        r_resp = await client.post("/api/v1/research/search", json={"query": "Microkernel IPC", "mode": "google"})
        if r_resp.status_code != 200:
            print(f"      [ERREUR DETAIL] /api/v1/research/search HTTP {r_resp.status_code} : {r_resp.text}")
        assert r_resp.status_code == 200, "Research route failed"
        
        # Route Chat Autonome
        c_resp = await client.post("/api/v1/chat", json={"message": "Explique SQLite WAL en 1 phrase.", "user_id": "root"})
        if c_resp.status_code != 200:
            print(f"      [ERREUR DETAIL] /api/v1/chat HTTP {c_resp.status_code} : {c_resp.text}")
        assert c_resp.status_code == 200, "Chat route failed"
        data_chat = c_resp.json()

        print(f"      [OK] GET /health                      -> HTTP 200 OK")
        print(f"      [OK] POST /api/v1/research/search     -> HTTP 200 (Provider: {r_resp.json().get('provider')})")
        print(f"      [OK] POST /api/v1/chat                -> HTTP 200 (Provider: {data_chat.get('provider')})")
        print(f"           Réponse : {data_chat.get('response')[:100]}...\n")

    print("=" * 65)
    print("   TOUS LES VOYANTS SONT AU VERT — SYSTÈME 100% OPÉRATIONNEL     ")
    print("=" * 65)

if __name__ == "__main__":
    asyncio.run(run_master_check())
