"""
E-ZZIO V7.28.10 — Identity Mirror
Affiche l'essence, les valeurs et le caractère d'E-ZZIO.
"""
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_DIR = ROOT_DIR / "config"

def mirror_identity():
    const_path = CONFIG_DIR / "constitution.json"
    persona_path = CONFIG_DIR / "persona.json"

    constitution = json.loads(const_path.read_text(encoding="utf-8"))
    persona = json.loads(persona_path.read_text(encoding="utf-8"))

    print("============================================================")
    print("  E-ZZIO — MIROIR D'IDENTITÉ (L'ESSENCE RETROUVÉE)")
    print("============================================================\n")

    print(f"NOM : {constitution.get('name')}")
    print(f"VERSION : {constitution.get('version')}")
    print("\n--- CONSTITUTION (LES VALEURS FONDAMENTALES) ---")
    for i, axiom in enumerate(constitution.get('axioms', []), 1):
        print(f"{i}. {axiom}")

    print("\n--- PERSONA (LE CARACTÈRE) ---")
    traits = persona.get('traits', {})
    for k, v in traits.items():
        print(f"{k.upper()} : {v}")

    print("\n============================================================")
    print("  La personnalité est intacte. Le code n'est que l'enveloppe.")
    print("============================================================\n")

if __name__ == "__main__":
    mirror_identity()
