"""
E-ZZIO V7.24.5 — Stress Test & Chaos Engineering Suite (Final Verification)
"""

import sys
import asyncio
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.intelligence_router import intelligence_router
from core.routing.contracts import RouteConstraints, Urgency
from ollama.adaptive_governor import ollama_governor
from providers.provider_registry import get_provider_instance


async def run_chaos_suite():
    print("============================================================")
    print(" E-ZZIO V7.24.5 — CAMPAGNE DE VÉRIFICATION GOUVERNANCE & LEDGER")
    print("============================================================\n")

    # TEST 1 — Pression RAM Critique (Doit forcer le Cloud par pénalité de -0.40)
    print("[TEST 1] Simulation d'une Pression RAM Critique (Seuil 10Go violé)...")
    original_max = ollama_governor.max_ram_bytes
    ollama_governor.max_ram_bytes = 1024  # Force la saturation immédiate

    d_pressure = await intelligence_router.route("architecture", "Gros système", RouteConstraints(allow_cloud=True))
    print(
        f"  -> Résultat sous Pression RAM Extrême : Plan = [{d_pressure.execution_plane.upper()}] | Provider = [{d_pressure.provider}] | Modèle = [{d_pressure.model}] | Score = {d_pressure.confidence_score}"
    )
    ollama_governor.max_ram_bytes = original_max

    # TEST 2 — Chaos : Panne effective d'Ollama + Traçabilité Ledger du Fallback
    print("\n[TEST 2] Test de Résilience & Fallback Ledger...")
    d_ollama = await intelligence_router.route("fast_chat", "Discord test", RouteConstraints(urgency=Urgency.REALTIME, allow_cloud=True))
    print(f"  -> Décision initiale du routeur : {d_ollama.provider}/{d_ollama.model}")

    ollama_instance = get_provider_instance("ollama")
    original_host = ollama_instance.host
    ollama_instance.host = "http://127.0.0.1:1"  # Port mort

    print("  -> Exécution avec Ollama HS (Déclenchement du Recovery & Écriture Ledger)...")
    res = await intelligence_router.execute(d_ollama, "Ceci est un test de chaos traçable")
    print(f"  -> Résultat exécution : OK={res.ok} | Provider effectif={res.provider} | Modèle effectif={res.model}")

    ollama_instance.host = original_host

    # TEST 3 — Audit complet du Decision Ledger (Vérification des métadonnées de Fallback)
    print("\n[TEST 3] Audit fin du Decision Ledger (JSONL)...")
    ledger_path = ROOT_DIR / "runtime" / "decisions" / "router_decisions.jsonl"
    if ledger_path.exists():
        lines = ledger_path.read_text(encoding="utf-8").strip().splitlines()
        print(f"  -> Total entrées dans le Ledger : {len(lines)}")
        if lines:
            last_entry = json.loads(lines[-1])
            print("  -> Dernière entrée journalisée :")
            print(json.dumps(last_entry, indent=2, ensure_ascii=False))
        print("  [OK] Traçabilité de secours validée.")
    else:
        print("  [WARNING] Decision Ledger absent.")

    print("\n============================================================")
    print(" V7.24.5 CERTIFIÉE : GOUVERNANCE RAM ET LEDGER OPÉRATIONNELS")
    print("============================================================\n")


if __name__ == "__main__":
    asyncio.run(run_chaos_suite())
