import os
import sys
import json
from pathlib import Path

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
REGISTRY_OUT.mkdir(parents=True, exist_ok=True)

def deep_inspect_contracts():
    print("[*] Inspection profonde des contrats déclaratifs existants...")
    contracts_data = []

    for p in ROOT_DIR.rglob("*.contract.json"):
        if any(ex in p.parts for ex in {".git", "__pycache__", "venv", "node_modules", "runtime/audit"}):
            continue
        try:
            raw_content = p.read_text(encoding="utf-8", errors="replace")
            parsed_json = json.loads(raw_content)
            
            # Analyse structurelle par blocs fonctionnels
            profile = {
                "file_path": str(p.relative_to(ROOT_DIR)).replace("\\", "/"),
                "identity": {
                    "model_id": parsed_json.get("model_id"),
                    "contract_version": parsed_json.get("contract_version"),
                    "provider": parsed_json.get("provider")
                },
                "trust": parsed_json.get("trust", {}),
                "resources": parsed_json.get("resources", {}),
                "security": parsed_json.get("security", {}),
                "integrity_and_signature": {
                    "has_signature_field": "signature" in parsed_json,
                    "signature_value": parsed_json.get("signature"),
                    "integrity_block": parsed_json.get("integrity", {})
                },
                "raw_keys": list(parsed_json.keys())
            }
            contracts_data.append(profile)
        except Exception as e:
            contracts_data.append({
                "file_path": str(p.relative_to(ROOT_DIR)).replace("\\", "/"),
                "error": str(e)
            })

    # Sauvegarde du rapport JSON
    out_json = REGISTRY_OUT / "contracts_deep_inspection.json"
    out_json.write_text(json.dumps(contracts_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # Génération du rapport Markdown d'inspection
    build_inspection_markdown(contracts_data)
    print(f"[OK] Inspection terminée. Rapport enregistré dans {out_json}")

def build_inspection_markdown(contracts: list):
    md_path = REGISTRY_OUT / "CONTRACT_DEEP_INSPECTION.md"
    lines = [
        "# E-ZZIO V7.4.1 — Rapport d'Inspection Profonde des Contrats",
        f"**Nombre total de contrats inspectés :** {len(contracts)}",
        ""
    ]

    for idx, c in enumerate(contracts, 1):
        if "error" in c:
            lines.append(f"## Contrat {idx} : `{c['file_path']}` (ERREUR)")
            lines.append(f"- **Erreur :** `{c['error']}`")
            continue

        iden = c["identity"]
        trust = c["trust"]
        res = c["resources"]
        sec = c["security"]
        sig = c["integrity_and_signature"]

        lines.extend([
            f"## Contrat {idx} : `{c['file_path']}`",
            f"- **Model ID :** `{iden.get('model_id')}`",
            f"- **Version :** `{iden.get('contract_version')}`",
            f"- **Provider :** `{iden.get('provider')}`",
            f"- **Bloc Trust :** `{trust}`",
            f"- **Ressources / Hardware :**",
            f"  - Workers max : `{res.get('max_allowed_workers')}`",
            f"  - RAM max (MB) : `{res.get('max_ram_mb')}`",
            f"  - GPU autorisé : `{res.get('gpu_allowed')}`",
            f"- **Sécurité :**",
            f"  - Attestation requise : `{sec.get('requires_attestation')}`",
            f"  - Ledger requis : `{sec.get('ledger_required')}`",
            f"- **Signature & Intégrité :**",
            f"  - Présence de signature : `{sig.get('has_signature_field')}`",
            f"  - Valeur (tronquée) : `{str(sig.get('signature_value'))[:16]}...`" if sig.get('signature_value') else "  - Valeur : `None / PENDING`",
            f"  - Blocs intégrité additionnels : `{sig.get('integrity_block')}`",
            f"- **Clés brutes du schéma :** `{c['raw_keys']}`",
            ""
        ])

    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Synthèse Markdown générée : {md_path}")

if __name__ == "__main__":
    deep_inspect_contracts()
