import sys
import asyncio
sys.path.insert(0, r'G:\AI\E-zzio')

from runtime.realtime.pipecat.router import EzzioRealtimeRouter

async def diagnostic():
    print("=" * 60)
    print(" E-ZZIO V7 — DIAGNOSTIC ISOLÉ EZZIO REALTIME ROUTER")
    print("=" * 60)
    
    router = EzzioRealtimeRouter()
    prompt = "Bonjour E-ZZIO, donne-moi un conseil court."
    print(f"Prompt injecté : \"{prompt}\"")
    
    try:
        res = await router.process(text=prompt, task="conversation")
        print(f"Résultat brut du routeur : {res}")
    except Exception as e:
        print(f"🔴 Exception levée par le routeur : {e}")

if __name__ == "__main__":
    asyncio.run(diagnostic())
