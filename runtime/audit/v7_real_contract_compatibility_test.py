import os
import sys
import json
import hashlib
import hmac
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
REGISTRY_OUT.mkdir(parents=True, exist_ok=True)

def inspect_contract_signer_implementation():
    signer_file = ROOT_DIR / "runtime" / "hardware" / "trust" / "models" / "contract_signer.py"
    if not signer_file.exists():
        return {"error": "contract_signer.py introuvable"}
    
    content = signer_file.read_text(encoding="utf-8", errors="replace")
    serialization_clues = [line.strip() for line in content.splitlines() if "json" in line or "dumps" in line or "encode" in line]
    key_clues = [line.strip() for line in content.splitlines() if "secret" in line.lower() or "key" in line.lower() or "seed" in line.lower()]

    return {
        "file_path": "runtime/hardware/trust/models/contract_signer.py",
        "serialization_clues": serialization_clues[:10],
        "key_clues": key_clues[:10]
    }

def run_real_contract_compatibility_test():
    print("[*] Démarrage du test de compatibilité des contrats réels V7.9.1...")
    
    contract_file = ROOT_DIR / "runtime" / "hardware" / "trust" / "models" / "contracts" / "qwen2.5-7b.contract.json"
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "contract_file_exists": contract_file.exists(),
        "signer_implementation_analysis": inspect_contract_signer_implementation()
    }

    if contract_file.exists():
        raw_text = contract_file.read_text(encoding="utf-8")
        contract_json = json.loads(raw_text)
        
        real_signature = contract_json.get("signature")
        results["contract_metadata"] = {
            "model_id": contract_json.get("model_id"),
            "provider": contract_json.get("provider"),
            "real_signature_present": bool(real_signature),
            "real_signature_value": real_signature
        }

        clean_payload = {k: v for k, v in contract_json.items() if k != "signature"}
        
        # Variantes de sérialisation possibles
        p1 = json.dumps(clean_payload, sort_keys=True, separators=(',', ':')).encode("utf-8")
        p2 = json.dumps(clean_payload, indent=2).encode("utf-8")
        p3 = json.dumps(clean_payload, separators=(',', ':')).encode("utf-8")

        possible_keys = ["ezzio-secret-seed", "default_secret", "EZZIO_SECRET", ""]
        key_file = ROOT_DIR / "runtime" / "hardware" / "security" / "hmac.key"
        if key_file.exists():
            try:
                possible_keys.insert(0, key_file.read_text(encoding="utf-8").strip())
            except UnicodeDecodeError:
                # Si la clé est binaire, on convertit en hex ou on utilise les octets bruts
                raw_key_bytes = key_file.read_bytes()
                possible_keys.insert(0, raw_key_bytes.hex())
                possible_keys.insert(0, raw_key_bytes.decode("latin1"))

        match_found = False
        matched_details = {}

        for key in possible_keys:
            if not key: continue
            for name, payload_bytes in [("canonical_sorted", p1), ("json_indent", p2), ("json_compact", p3)]:
                legacy_hash = hashlib.sha256(payload_bytes + key.encode("utf-8", errors="ignore")).hexdigest()
                if real_signature and hmac.compare_digest(legacy_hash, real_signature):
                    match_found = True
                    matched_details = {"key_used_type": "discovered_key", "serialization": name, "algorithm": "legacy_sha256_payload_plus_secret"}
                    break
                
                hmac_hash = hmac.new(key.encode("utf-8", errors="ignore"), payload_bytes, hashlib.sha256).hexdigest()
                if real_signature and hmac.compare_digest(hmac_hash, real_signature):
                    match_found = True
                    matched_details = {"key_used_type": "discovered_key", "serialization": name, "algorithm": "hmac_sha256"}
                    break
            if match_found: break

        results["compatibility_test"] = {
            "legacy_signature_reproduced": match_found,
            "match_details": matched_details if match_found else "Aucune combinaison clé/sérialisation n'a permis de reproduire exactement la signature stockée dans le contrat."
        }
    else:
        results["compatibility_test"] = {"error": "Fichier qwen2.5-7b.contract.json introuvable"}

    out_json = REGISTRY_OUT / "real_contract_compatibility_result.json"
    out_json.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    build_markdown(results)
    print(f"[OK] Test V7.9.1 terminé. Rapport généré dans {REGISTRY_OUT}")

def build_markdown(res: dict):
    md_path = REGISTRY_OUT / "V7_REAL_CONTRACT_COMPATIBILITY_REPORT.md"
    compat = res.get("compatibility_test", {})
    meta = res.get("contract_metadata", {})
    signer = res.get("signer_implementation_analysis", {})

    lines = [
        "# E-ZZIO V7.9.1 — Rapport de Test de Compatibilité Réelle des Contrats",
        f"**Date :** {res.get('timestamp')}",
        "",
        "## 1. Métadonnées du Contrat Réel",
        f"- **Fichier analysé :** `runtime/hardware/trust/models/contracts/qwen2.5-7b.contract.json`",
        f"- **Model ID :** `{meta.get('model_id')}`",
        f"- **Provider :** `{meta.get('provider')}`",
        f"- **Signature présente :** `{meta.get('real_signature_present')}`",
        f"- **Valeur de signature :** `{meta.get('real_signature_value')}`",
        "",
        "## 2. Analyse de l'Implémentation de `contract_signer.py`",
        f"- **Indices de sérialisation :** `{signer.get('serialization_clues')}`",
        f"- **Indices de clé :** `{signer.get('key_clues')}`",
        "",
        "## 3. Résultats du Test de Compatibilité & Reproduction",
        f"- **LEGACY_SIGNATURE_REPRODUCED :** `{compat.get('legacy_signature_reproduced', False)}`",
        f"- **Détails du match :** `{compat.get('match_details')}`",
        "",
        "## 4. Conclusion de l'Étape V7.9.1",
        "Ce test démontre si la signature actuelle du contrat peut être validée par une fonction de dérivation déterministe ou si une ré-émission des contrats sera nécessaire lors de la bascule vers l'autorité HMAC unifiée."
    ]

    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Rapport Markdown généré : {md_path}")

if __name__ == "__main__":
    run_real_contract_compatibility_test()
