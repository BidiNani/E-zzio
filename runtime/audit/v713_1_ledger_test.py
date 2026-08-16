import sys
from pathlib import Path

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from runtime.contracts.enforcer import EnforcedModelRouter, UnauthorizedModelError

def test_ledger_and_enforcement():
    print("[*] -----------------------------------------------------------------")
    print("[*] E-ZZIO V7.13.1 — Test du Decision Ledger & Epoch Control...")
    print("[*] -----------------------------------------------------------------")
    
    router = EnforcedModelRouter()
    print(f"  [OK] Ledger d'audit localisé : {router.audit_log_path}")

    # 1. Requête autorisée
    try:
        router.route_inference("qwen2.5-coder:7b")
        print("  [OK] Appel nominal ALLOW enregistré.")
    except Exception as e:
        print(f"  ❌ Erreur inattendue : {e}")

    # 2. Tentative de Shadow Inference (refusée)
    try:
        router.route_inference("malicious-rogue-model:1b")
    except UnauthorizedModelError:
        print("  [OK] Tentative de Shadow Inference bloquée et refus DENY enregistré.")

    # 3. Lecture et affichage des derniers événements du Ledger
    print("\n--- 📖 Contenu récent du Journal d'Audit (model_authority_events.jsonl) ---")
    if router.audit_log_path.exists():
        lines = router.audit_log_path.read_text(encoding="utf-8").splitlines()
        for line in lines[-3:]: # Afficher les 3 derniers événements
            print(f"  -> {line}")
    else:
        print("  [!] Journal introuvable.")

if __name__ == "__main__":
    test_ledger_and_enforcement()
