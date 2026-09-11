"""
E-ZZIO V7.29 — Sovereign Boot Sequence
Orchestre l'initialisation sécurisée :
1. Audit de l'empreinte identitaire globale (Constitution, Persona, Lore).
2. Vérification d'intégrité et boot recovery du Decision Ledger.
3. Autorisation du Runtime.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.identity.identity_boot_check import verify_system_identity
from core.security.ledger_engine import ledger_engine


def boot_system() -> bool:
    print("============================================================")
    print(" E-ZZIO V7.29 — SOUVEREIGN RUNTIME BOOT SEQUENCE")
    print("============================================================\n")

    # Étape 1 : Vérification de l'empreinte identitaire globale (ADN)
    if not verify_system_identity():
        print("[X] BOOT INTERROMPU : Échec de la certification identitaire.")
        return False

    # Étape 2 : Initialisation et vérification du Decision Ledger (Mémoire/Gouvernance)
    if ledger_engine.system_mode == "FAIL_CLOSED":
        print("[X] BOOT INTERROMPU : Ledger en mode FAIL-CLOSED (intégrité compromise).")
        return False

    print("\n[OK] SYSTEM STATUS : RUNTIME SOUVERAIN OPÉRATIONNEL")
    print("============================================================\n")
    return True


if __name__ == "__main__":
    success = boot_system()
    sys.exit(0 if success else 1)
