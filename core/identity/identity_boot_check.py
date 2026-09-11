"""
E-ZZIO V7.29 — Boot Identity Verification
Vérifie la cohérence totale de l'identité avant d'autoriser le runtime.
"""

from core.identity.global_fingerprint import global_fingerprint
from core.identity.identity_validator import identity_validator


def verify_system_identity() -> bool:
    print("[*] Audit de l'empreinte identitaire globale...")
    root_hash = global_fingerprint.compute_identity_root()
    audit_report = identity_validator.audit_identity()

    is_valid = audit_report.get("identity_status") == "PRESERVED"

    print(f"  -> Global Identity Root Hash : {root_hash[:16]}...")
    print(f"  -> Statut des composants : {audit_report.get('identity_status')}")

    if not is_valid:
        print("[!] ALERTE CRITIQUE : Dérive identitaire ou altération de la Constitution détectée !")
        return False

    print("[OK] Identité souveraine certifiée et liée au runtime.")
    return True
