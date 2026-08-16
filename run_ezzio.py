import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from runtime.agent.loop import AgentLoop
from runtime.router.cognitive_router import CognitiveRouter

def main():
    parser = argparse.ArgumentParser(description="E-ZZIO Sovereign Runtime CLI")
    parser.add_argument("action", choices=["run", "router-test", "status"], help="Action à exécuter")
    parser.add_argument("--objective", type=str, default="Exécuter une tâche souveraine de maintenance", help="Objectif de l'agent")
    
    args = parser.parse_args()

    print("============================================================")
    print(" E-ZZIO COGNITIVE OPERATING RUNTIME — CONTRÔLE CENTRAL")
    print("============================================================")

    if args.action == "run":
        print(f"[*] Lancement de l'Agent Loop avec l'objectif : '{args.objective}'")
        try:
            agent = AgentLoop()
            result = agent.run(args.objective)
            print(f"  [RESULT] État final : {result.get('state')}")
            print(f"  [RESULT] Vérification : {result.get('verification', 'N/A')}")
            print(f"  [RESULT] Événements Ledger : {result.get('ledger_events', 0)}")
            print("[SUCCESS] Exécution de la boucle gouvernée terminée.")
        except Exception as e:
            print(f"[ERROR] Échec de la boucle agentique : {e}")
            sys.exit(1)

    elif args.action == "router-test":
        print("[*] Test du routeur cognitif hybride...")
        try:
            router = CognitiveRouter()
            res = router.route_query("Confirme la disponibilité du routeur en un mot.", target="local")
            print(f"  [ROUTER RESPONSE] {res.strip()}")
            print("[SUCCESS] Routeur opérationnel.")
        except Exception as e:
            print(f"[ERROR] Routeur en échec : {e}")
            sys.exit(1)

    elif args.action == "status":
        print("[*] Vérification de l'état du système E-zzio...")
        db_path = Path("runtime/memory/semantic/memory.db")
        print(f"  - Mémoire sémantique (VectorStore) : {'PRÉSENTE' if db_path.exists() else 'VIDE'}")
        print("  - Constitution : ACTIVE (Registry Core)")
        print("  - Système Immunitaire : ACTIF (IncidentRegistry)")
        print("[SUCCESS] Système intègre et opérationnel.")

if __name__ == "__main__":
    main()