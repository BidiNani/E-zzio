import sys
import asyncio
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path: sys.path.insert(0, str(ROOT_DIR))

from core.intelligence_router import intelligence_router
from core.routing.contracts import RouteConstraints, Urgency

async def run_matrix():
    print("=== E-ZZIO V7.24.2.1 ROUTER DECISION MATRIX ===")

    # CAS 1 : Discord rapide
    d1 = await intelligence_router.route("fast_chat", "Salut", RouteConstraints(urgency=Urgency.REALTIME))
    print(f"\n[CAS 1 - Discord Rapide] Choix attendu: gemma ou groq -> Obtenu: {d1.provider}/{d1.model} (Score: {d1.confidence_score})")

    # CAS 2 : Refactoring Python
    d2 = await intelligence_router.route("coding", "Refactor ce script", RouteConstraints(urgency=Urgency.NORMAL))
    print(f"[CAS 2 - Coding] Choix attendu: qwen2.5-coder -> Obtenu: {d2.provider}/{d2.model} (Score: {d2.confidence_score})")

    # CAS 3 : Cloud favorisé (Simulation tâche lourde)
    d3 = await intelligence_router.route("architecture", "Analyse système", RouteConstraints(urgency=Urgency.DEEP))
    print(f"[CAS 3 - Architecture] Choix attendu: qwen3 ou gemini -> Obtenu: {d3.provider}/{d3.model} (Score: {d3.confidence_score})")

    # CAS 4 : Confidentialité Stricte
    d4 = await intelligence_router.route("analysis", "Données RH", RouteConstraints(require_privacy=True))
    print(f"[CAS 4 - Privacy] Choix attendu: ollama (qwen3) -> Obtenu: {d4.provider}/{d4.model} (Score: {d4.confidence_score})")

    # CAS 5 : Vision
    d5 = await intelligence_router.route("vision", "Que vois-tu ?", RouteConstraints(require_vision=True))
    print(f"[CAS 5 - Vision] Choix attendu: qwen2.5vl ou gemini -> Obtenu: {d5.provider}/{d5.model} (Score: {d5.confidence_score})")

if __name__ == "__main__":
    asyncio.run(run_matrix())
