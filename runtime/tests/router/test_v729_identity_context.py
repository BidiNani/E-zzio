"""
E-ZZIO V7.29.0 — Unit Test for Identity Context
Valide l'intégrité de la génération du Root Hash et du Sceau d'Identité.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.identity.identity_context import IdentityContext

def run_unit_test():
    print("============================================================")
    print(" E-ZZIO V7.29.0 — UNIT TEST: IDENTITY CONTEXT")
    print("============================================================\n")

    ctx = IdentityContext()
    payload = ctx.export_context()

    print(f"  -> Constitution Hash : {payload['constitution_hash'][:16]}...")
    print(f"  -> Persona Hash      : {payload['persona_hash'][:16]}...")
    print(f"  -> Identity Root     : {payload['identity_root_hash']}")
    print(f"  -> Identity Seal     : {payload['identity_seal'][:32]}...")

    assert len(payload['identity_root_hash']) == 64, "Le Root Hash n'est pas un SHA-256 valide !"
    assert len(payload['identity_seal']) == 64, "Le Sceau HMAC n'est pas valide !"
    assert payload['signer'] == "E-ZZIO Sovereign Kernel", "Signataire non conforme !"

    print("\n[OK] TEST UNITAIRE RÉUSSI : Identity Context généré et scellé.")
    print("============================================================\n")

if __name__ == "__main__":
    run_unit_test()
