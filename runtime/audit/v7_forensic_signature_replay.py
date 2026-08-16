import os
import sys
import json
import hashlib
import hmac
import re
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
REGISTRY_OUT.mkdir(parents=True, exist_ok=True)

def inspect_source_code(file_path: Path) -> str:
    if not file_path.exists():
        return f"[ERREUR] {file_path} introuvable."
    return file_path.read_text(encoding="utf-8", errors="replace")

def run_forensic_replay():
    print("[*] Démarrage du Forensic Replay des signatures (Mode Read-Only)...")
    
    signer_file = ROOT_DIR / "runtime" / "hardware" / "trust" / "models" / "contract_signer.py"
    registry_file = ROOT_DIR / "runtime" / "hardware" / "trust" / "models" / "registry.py"
    contract_file = ROOT_DIR / "runtime" / "hardware" / "trust" / "models" / "contracts" / "qwen2.5-7b.contract.json"
    
    signer_code = inspect_source_code(signer_file)
    registry_code = inspect_source_code(registry_file)
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "signer_code_snippet": signer_code[:1500],
        "registry_code_snippet": registry_code[:1500],
        "permutations_tested": []
    }

    if not contract_file.exists():
        print("[ERREUR] Contrat qwen2.5-7b.contract.json introuvable.")
        return

    raw_text = contract_file.read_text(encoding="utf-8")
    contract_json = json.loads(raw_text)
    stored_signature = contract_json.get("signature")
    
    results["stored_signature"] = stored_signature

    clean_payload = {k: v for k, v in contract_json.items() if k != "signature"}

    keys_to_test = ["ezzio-secret-seed", "default_secret", "EZZIO_SECRET", "secret", ""]
    key_file = ROOT_DIR / "runtime" / "hardware" / "security" / "hmac.key"
    if key_file.exists():
        try:
            keys_to_test.insert(0, key_file.read_text(encoding="utf-8").strip())
        except Exception:
            raw_b = key_file.read_bytes()
            keys_to_test.insert(0, raw_b.hex())
            keys_to_test.insert(0, raw_b.decode("latin1", errors="ignore"))

    serialization_variants = [
        ("json_sort_keys_compact", json.dumps(clean_payload, sort_keys=True, separators=(',', ':'))),
        ("json_sort_keys_spaces", json.dumps(clean_payload, sort_keys=True, indent=2)),
        ("json_raw_compact", json.dumps(clean_payload, separators=(',', ':'))),
        ("json_raw_pretty", json.dumps(clean_payload, indent=2)),
        ("raw_text_regex_stripped", re.sub(r',\s*"signature":\s*"[^"]*"', '', raw_text))
    ]

    match_found = False
    for key in keys_to_test:
        if not key: continue
        for ser_name, ser_data in serialization_variants:
            payload_bytes = ser_data.encode("utf-8") if isinstance(ser_data, str) else ser_data
            
            h_a = hashlib.sha256(payload_bytes + key.encode("utf-8", errors="ignore")).hexdigest()
            h_b = hashlib.sha256(key.encode("utf-8", errors="ignore") + payload_bytes).hexdigest()
            h_c = hmac.new(key.encode("utf-8", errors="ignore"), payload_bytes, hashlib.sha256).hexdigest()

            if stored_signature and (h_a == stored_signature or h_b == stored_signature or h_c == stored_signature):
                match_found = True
                results["permutations_tested"].append({
                    "status": "MATCH",
                    "key_used": key[:10] + "...",
                    "serialization": ser_name,
                    "algorithm": "sha256(payload+key)" if h_a == stored_signature else ("sha256(key+payload)" if h_b == stored_signature else "hmac")
                })
                break
        if match_found: break

    if not match_found:
        results["permutations_tested"].append({
            "status": "NO_MATCH",
            "message": "Aucune combinaison n'a produit la signature stockée. La clé de signature originelle est probablement externe ou un sel système spécifique a été utilisé."
        })

    out_json = REGISTRY_OUT / "forensic_signature_replay.json"
    out_json.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    build_markdown(results, signer_file, registry_file)
    print(f"[OK] Forensic Replay terminé. Rapport enregistré dans {REGISTRY_OUT}")

def build_markdown(res: dict, signer_file: Path, registry_file: Path):
    md_path = REGISTRY_OUT / "FORENSIC_SIGNATURE_REPLAY.md"
    
    lines = [
        "# E-ZZIO V7.9.2 — Rapport de Forensic Replay des Signatures",
        f"**Date :** {res.get('timestamp')}",
        "",
        "## 1. Données Cibles",
        f"- **Signature stockée dans le contrat :** `{res.get('stored_signature')}`",
        f"- **Fichier de signature analysé :** `{signer_file.name}`",
        f"- **Fichier de registre analysé :** `{registry_file.name}`",
        "",
        "## 2. Résultats des Tests de Replay",
    ]

    for p in res.get("permutations_tested", []):
        lines.append(f"- **Statut :** `{p.get('status')}`")
        if p.get('status') == 'MATCH':
            lines.append(f"  - **Sérialisation :** `{p.get('serialization')}`")
            lines.append(f"  - **Algorithme :** `{p.get('algorithm')}`")
            lines.append(f"  - **Clé validée :** `{p.get('key_used')}`")
        else:
            lines.append(f"  - **Message :** `{p.get('message')}`")

    lines.extend([
        "",
        "## 3. Analyse du Code Source (`contract_signer.py`)",
        "```python",
        res.get("signer_code_snippet", "")[:800],
        "```",
        "",
        "## 4. Conclusion Forensic",
        "L'échec de la reproduction directe indique que la signature d'origine a été émise avec un contexte de clé ou un hachage intermédiaire spécifique qu'il convient d'isoler en lisant directement `contract_signer.py` avant toute migration."
    ])

    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Rapport Markdown généré : {md_path}")

if __name__ == "__main__":
    run_forensic_replay()
