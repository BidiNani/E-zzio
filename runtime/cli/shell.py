import sys
from pathlib import Path

# Injection de la racine du projet pour garantir la résolution absolue des modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runtime.cli.session import SessionContext
from runtime.cli.commands import CommandHandler


def run_shell():
    session = SessionContext()
    handler = CommandHandler()

    print("============================================================")
    print(" E-ZZIO INTERACTIVE SHELL — COCKPIT HUMAIN (v4.2.2)")
    print(" Tapez 'status', 'skills list', 'analyze <file>', 'search <query>', ou 'exit'")
    print("============================================================")

    while True:
        try:
            user_input = input("ezzio> ").strip()
            if not user_input:
                continue

            session.record(user_input)
            response = handler.handle(user_input)

            if response == "EXIT":
                print("Fermeture de la session interactive. Au revoir.")
                break

            print(response)
            print("-" * 60)
        except (KeyboardInterrupt, EOFError):
            print("\nSession interrompue. Arrêt propre.")
            break


if __name__ == "__main__":
    run_shell()
