"""
E-ZZIO V7.29.3 — Certification Test Suite (Identity Guardian)
Valide l'audit dynamique en temps réel et la bascule en FAIL_CLOSED.
"""

import sys
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.identity.identity_context import ImmutableIdentityContext
from core.identity.identity_guardian import IdentityGuardian
from core.identity.identity_events import IdentityState
from core.identity.identity_validator import identity_validator


def run_guardian_certification():
    print("============================================================")
    print(" E-ZZIO V7.29.3 — IDENTITY GUARDIAN CERTIFICATION (10/10)")
    print("============================================================\n")

    persona_path = ROOT_DIR / "config" / "persona.json"
    orig_persona = persona_path.read_text(encoding="utf-8")

    try:
        # 1. Vérification des scellements de persistance
        val_res = identity_validator.validate_persistence_seals()
        assert val_res["valid"] is True, f"Seals invalides : {val_res.get('error')}"
        print("  [1/4] Ancres de persistance et signatures HMAC validées.")

        # 2. Boot & Instanciation du Guardian
        ctx = ImmutableIdentityContext()
        guardian = IdentityGuardian(ctx)

        audit_initial = guardian.audit_now()
        assert audit_initial["valid"] is True, "Audit initial échoué !"
        assert audit_initial["state"] == IdentityState.VERIFIED
        print(f"  [2/4] Boot réussi : Session {ctx.boot_session_id} | State: {audit_initial['state']}")

        # 3. Attaque par modification du Persona Kernel à chaud
        print("\n  [!] SIMULATION D'ATTAQUE : Altération du Persona Kernel...")
        persona_data = json.loads(orig_persona)
        persona_data["traits"]["seriousness"] = 0
        persona_path.write_text(json.dumps(persona_data, indent=2), encoding="utf-8")

        # 4. Exécution de l'audit Guardian
        audit_attack = guardian.audit_now()
        print(f"  -> Résultat Guardian post-attaque : {audit_attack}")

        assert audit_attack["valid"] is False, "Le Guardian n'a pas intercepté l'altération !"
        assert audit_attack["state"] == IdentityState.FAIL_CLOSED, "Bascule en FAIL_CLOSED non effectuée !"
        print("  [3/4] Dérive identitaire interceptée avec succès -> Machine d'état verrouillée en FAIL_CLOSED.")

        # 5. Tentative d'audit subséquent en état FAIL_CLOSED
        audit_blocked = guardian.audit_now()
        assert audit_blocked["state"] == IdentityState.FAIL_CLOSED
        print("  [4/4] Verrouillage FAIL_CLOSED persistant confirmé.")

        print("\n============================================================")
        print(" V7.29.3 CERTIFIÉ : IDENTITY RUNTIME GUARDIAN OPÉRATIONNEL")
        print("============================================================\n")

    finally:
        persona_path.write_text(orig_persona, encoding="utf-8")


if __name__ == "__main__":
    run_guardian_certification()
