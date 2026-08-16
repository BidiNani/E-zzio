import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
REGISTRY_OUT.mkdir(parents=True, exist_ok=True)

def run_evidence_bundle():
    print("[*] Génération du Cryptographic Evidence Bundle V7.9.5...")
    
    contract_file = ROOT_DIR / "runtime" / "hardware" / "trust" / "models" / "contracts" / "qwen2.5-7b.contract.json"
    if not contract_file.exists():
        print("[ERREUR] Contrat qwen2.5-7b.contract.json introuvable.")
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
    key_source_map = {}
    
    key_file = ROOT_DIR / "runtime" / "hardware" / "security" / "hmac.key"
    if key_file.exists():
        try:
            k_val = key_file.read_text(encoding="utf-8", errors="ignore").strip()
            candidate_secrets.insert(0, k_val)
            key_source_map[k_val] = str(key_file.relative_to(ROOT_DIR))
        except Exception:
            raw_b = key_file.read_bytes()
            hex_val = raw_b.hex()
            latin_val = raw_b.decode("latin1", errors="ignore")
            candidate_secrets.insert(0, hex_val)
            candidate_secrets.insert(0, latin_val)
            key_source_map[hex_val] = str(key_file.relative_to(ROOT_DIR))
            key_source_map[latin_val] = str(key_file.relative_to(ROOT_DIR))

    provenance_match = None

    for secret in set(candidate_secrets):
        if not secret: continue
        for ser_name, ser_string in serialization_variants:
            payload_bytes = ser_string.encode("utf-8")
            hash_val = hashlib.sha256(payload_bytes + secret.encode("utf-8", errors="ignore")).hexdigest()

            if hash_val == stored_signature:
                secret_id = hashlib.sha256(secret.encode("utf-8", errors="ignore")).hexdigest()[:16]
                source_path = key_source_map.get(secret, "ENV / Code / Hardcoded default")
                provenance_match = {
                    "contract": "qwen2.5-7b.contract.json",
                    "contract_sha256": hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
                    "payload_canonical_sha256": hashlib.sha256(payload_bytes).hexdigest(),
                    "stored_signature": stored_signature,
                    "reproduced_signature": hash_val,
                    "reproduced": True,
                    "algorithm": "SHA256(payload + secret)",
                    "serializer_variant": ser_name,
                    "secret_identifier": secret_id,
                    "source_path": source_path,
                    "timestamp": datetime.now().isoformat()
                }
                break
        if provenance_match: break

    if not provenance_match:
        provenance_match = {
            "contract": "qwen2.5-7b.contract.json",
            "stored_signature": stored_signature,
            "reproduced": False,
            "message": "Aucune combinaison n'a produit la signature stockée avec les secrets testés."
        }

    out_json = REGISTRY_OUT / "cryptographic_evidence_bundle.json"
    out_json.write_text(json.dumps(provenance_match, indent=2, ensure_ascii=False), encoding="utf-8")

    build_markdown(provenance_match)
    print(f"[OK] Evidence Bundle V7.9.5 généré dans {REGISTRY_OUT}")

def build_markdown(bundle: dict):
    md_path = REGISTRY_OUT / "V7_CRYPTOGRAPHIC_EVIDENCE_REPORT.md"
    reproduced = bundle.get("reproduced", False)

    lines = [
        "# E-ZZIO V7.9.5 — Cryptographic Evidence Bundle",
        f"**Date :** {datetime.now().isoformat()}",
        "",
        "## 1. Statut de l'Evidence Bundle",
        f"- **Signature Cible (Stockée) :** `{bundle.get('stored_signature')}`",
        f"- **Reproduction Mathématique :** `{str(reproduced).upper()}`",
        ""
    ]

    if reproduced:
        lines.extend([
            "## 2. Preuves Cryptographiques Validées",
            f"- **Algorithme validé :** `{bundle.get('algorithm')}`",
            f"- **Variante de sérialisation :** `{bundle.get('serializer_variant')}`",
            f"- **SHA-256 du Contrat Brut :** `{bundle.get('contract_sha256')}`",
            f"- **SHA-256 du Payload Canonique :** `{bundle.get('payload_canonical_sha256')}`",
            f"- **Identifiant du Secret (Hash masqué) :** `{bundle.get('secret_identifier')}`",
            f"- **Source du Secret :** `{bundle.get('source_path')}`",
        ])
    else:
        lines.extend([
            "## 2. Échec de la Preuve",
            f"- **Raison :** `{bundle.get('message')}`"
        ])

    lines.extend([
        "",
        "## 3. Statut Bloquant (Migration V7.10)",
        "Conformément au principe de précaution forensic, tant que la source exacte du secret n'est pas certifiée à 100% sans ambiguïté (et tant que l'écart avec l'autorité HMAC-SHA256 standard n'est pas ponté proprement), **la migration de la Trust Layer reste BLOQUÉE**."
    ])

    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Rapport Markdown Evidence Bundle généré : {md_path}")

if __name__ == "__main__":
    run_evidence_bundle()
