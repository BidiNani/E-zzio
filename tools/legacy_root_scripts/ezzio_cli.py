"""E-ZZIO Minimal Agent CLI — Direct Task Runner."""
import argparse

from core.agent.coding_agent_loop import CodingAgentHarness


def main():
    parser = argparse.ArgumentParser(description="E-ZZIO Autonomous Agent CLI")
    parser.add_argument("--backend", choices=["cloud_gemini", "local_qwen"], default="cloud_gemini",
                        help="Backend cognitif à utiliser (défaut: cloud_gemini)")
    parser.add_argument("--task", type=str, help="Tâche ponctuelle à exécuter directement")
    args = parser.parse_args()

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
