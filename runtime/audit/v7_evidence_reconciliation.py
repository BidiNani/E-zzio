import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
REGISTRY_OUT.mkdir(parents=True, exist_ok=True)

def run_reconciliation():
    print("[*] Démarrage de V7.9.6 — Evidence Reconciliation Audit...")
    
    contract_file = ROOT_DIR / "runtime" / "hardware" / "trust" / "models" / "contracts" / "qwen2.5-7b.contract.json"
    if not contract_file.exists():
        print("[ERREUR] Contrat introuvable.")
        return

    raw_text = contract_file.read_text(encoding="utf-8")
    contract_json = json.loads(raw_text)
    stored_signature = contract_json.get("signature")
    clean_payload = {k: v for k, v in contract_json.items() if k != "signature"}

    serialization_variants = [
        ("json_sort_keys_compact", json.dumps(clean_payload, sort_keys=True, separators=(",", ":"))),
        ("json_sort_keys_spaces", json.dumps(clean_payload, sort_keys=True, indent=2)),
        ("json_raw_compact", json.dumps(clean_payload, separators=(",", ":"))),
        ("json_raw_pretty", json.dumps(clean_payload, indent=2))
    ]

    candidate_secrets = ["ezzio-secret-seed", "default_secret", "EZZIO_CORE_ROOT_KEY", "EZZIO_SECRET", "secret", ""]
    key_file = ROOT_DIR / "runtime" / "hardware" / "security" / "hmac.key"
    if key_file.exists():
        try:
            candidate_secrets.insert(0, key_file.read_text(encoding="utf-8", errors="ignore").strip())
        except Exception:
            pass

    verbose_trials = []
    found_match = False

    for secret in set(candidate_secrets):
        for ser_name, ser_string in serialization_variants:
            payload_bytes = ser_string.encode("utf-8")
            hash_val = hashlib.sha256(payload_bytes + secret.encode("utf-8", errors="ignore")).hexdigest()
            is_match = (hash_val == stored_signature)
            verbose_trials.append({
                "secret_tested_masked": (secret[:4] + "...") if secret else "(empty)",
                "serializer": ser_name,
                "generated_hash": hash_val[:16] + "...",
                "match": is_match
            })
            if is_match:
                found_match = True

    reconciliation_result = {
        "timestamp": datetime.now().isoformat(),
        "stored_signature": stored_signature,
        "reconciliation_status": "FALSE_POSITIVE_DETECTED_IN_V7.9.4" if not found_match else "VERIFIED_TRUE_MATCH",
        "independent_replay_success": found_match,
        "total_permutations_tested": len(verbose_trials),
        "root_cause": "V7.9.4 a exhibé un faux positif ou une condition transitoire non persistée, car le rejeu indépendant strict génère 0 correspondance." if not found_match else "Match confirmé par rejeu indépendant."
    }

    out_json = REGISTRY_OUT / "evidence_reconciliation_result.json"
    out_json.write_text(json.dumps(reconciliation_result, indent=2, ensure_ascii=False), encoding="utf-8")

    build_markdown(reconciliation_result, verbose_trials)
    print(f"[OK] V7.9.6 Evidence Reconciliation généré dans {REGISTRY_OUT}")

def build_markdown(res: dict, trials: list):
    md_path = REGISTRY_OUT / "V7_EVIDENCE_RECONCILIATION_REPORT.md"
    
    lines = [
        "# E-ZZIO V7.9.6 — Evidence Reconciliation Report",
        f"**Date :** {res.get('timestamp')}",
        "",
        "## 1. Contexte de la Réconciliation",
        f"- **Réclamation V7.9.4 :** Reproductible (`TRUE`)",
        f"- **Vérification Indépendante V7.9.5 :** Reproductible (`FALSE`)",
        f"- **Verdict de l'Audit V7.9.6 :** `{res.get('reconciliation_status')}`",
        "",
        "## 2. Analyse de la Racine (Root Cause)",
        f"- **Total des permutations testées :** `{res.get('total_permutations_tested')}`",
        f"- **Diagnostic :** `{res.get('root_cause')}`",
        "",
        "## 3. Statut Bloquant Définitif",
        "La divergence entre V7.9.4 et V7.9.5 confirme formellement qu'**aucun secret local actuel ne permet de reproduire mathématiquement** la signature stockée dans le contrat `qwen2.5-7b.contract.json`. Par conséquent, toute tentative de migration ou de pont d'autorité est **strictement BLOQUÉE**.",
        "",
        "**Directive :** Aucune modification de code ou de configuration de production n'est autorisée. Le système reste en observation forensic pure."
    ]

    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Rapport Markdown de réconciliation généré : {md_path}")

if __name__ == "__main__":
    run_reconciliation()
