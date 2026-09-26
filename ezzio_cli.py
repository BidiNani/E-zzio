"""E-ZZIO Minimal Agent CLI — Direct Task Runner."""
import argparse

from core.agent.coding_agent_loop import CodingAgentHarness


def main():
    parser = argparse.ArgumentParser(description="E-ZZIO Autonomous Agent CLI")
    parser.add_argument("--backend", choices=["cloud_gemini", "local_qwen"], default="cloud_gemini",
                        help="Backend cognitif à utiliser (défaut: cloud_gemini)")
    parser.add_argument("--task", type=str, help="Tâche ponctuelle à exécuter directement")
    parser.add_argument("--doctor", action="store_true", help="Exécute les diagnostics E-ZZIO Doctor")
    parser.add_argument("--verify", action="store_true", help="Exécute les vérifications d'invariants E-ZZIO Verify")

    subparsers = parser.add_subparsers(dest="subcommand")
    subparsers.add_parser("doctor", help="Exécute les diagnostics système")
    subparsers.add_parser("verify", help="Exécute la vérification des invariants")

    args = parser.parse_args()

    if args.doctor or args.subcommand == "doctor":
        from core.observability.doctor import EzzioDoctor
        doctor = EzzioDoctor()
        print(doctor.format_report())
        return

    if args.verify or args.subcommand == "verify":
        from core.observability.verify import EzzioVerifier
        verifier = EzzioVerifier()
        res = verifier.verify_all()
        print("\n=======================================================")
        print(" E-ZZIO VERIFY — INVARIANT & CONTRACT VERIFICATION")
        print("=======================================================\n")
        all_ok = True
        for k, v in res.items():
            st = v.get("status", "UNKNOWN")
            print(f"[{st:<8}] {k:<25} : {v.get('details')}")
            if st not in ("PROVEN", "MEASURED", "OBSERVED"):
                all_ok = False
        print("=======================================================\n")
        return 0 if all_ok else 1

    print("\n=======================================================")
    print(f" E-ZZIO AGENTIC HARNESS (Backend: {args.backend})")
    print("=======================================================\n")

    agent = CodingAgentHarness(backend=args.backend)

    if args.task:
        run_task(agent, args.task)
        return

    # Mode interactif
    while True:
        try:
            prompt = input("\nE-ZZIO > ").strip()
            if not prompt:
                continue
            if prompt.lower() in ["exit", "quit", "q"]:
                print("[INFO] Fermeture de la session.")
                break

            run_task(agent, prompt)
        except KeyboardInterrupt:
            print("\n[INFO] Interruption par l'utilisateur.")
            break

def run_task(agent: CodingAgentHarness, prompt: str):
    print(f"\n[ACTION] Démarrage de la trajectoire pour : {prompt}\n")
    for event in agent.run_trajectory(prompt):
        step = event.get("step")
        thought = event.get("thought", "")
        action = event.get("action")
        observation = event.get("observation")

        print(f"--- [Étape {step}] ---")
        if thought:
            print(f"🧠 Pensée : {thought}")
        if action:
            print(f"⚡ Outil invoqué : {action.get('tool')} | Args: {action.get('args')}")
        if observation:
            obs_preview = str(observation)[:300] + ("..." if len(str(observation)) > 300 else "")
            print(f"👁️ Observation : {obs_preview}")
        print()

if __name__ == "__main__":
    main()
