import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import shutil

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
V712_REGISTRY = REGISTRY_OUT / "V712"
V712_REGISTRY.mkdir(parents=True, exist_ok=True)

def run_governance_freeze():
    print("[*] -----------------------------------------------------------------")
    print("[*] E-ZZIO V7.12.4 — Génération du Sceau de Gouvernance (Governance Freeze)...")
    print("[*] -----------------------------------------------------------------")

    # Fichiers sources de gouvernance à geler
    sources = {
        "api_contract": ROOT_DIR / "runtime" / "contracts" / "API_CONTRACT_V3.json",
        "certification_token": REGISTRY_OUT / "v712_certification_token.json",
        "architecture_baseline": REGISTRY_OUT / "architecture_baseline_v3.json",
        "entry_gate_report": REGISTRY_OUT / "V712_ENTRY_GATE_REPORT.md",
        "entry_gate_code": ROOT_DIR / "runtime" / "audit" / "gates" / "v712_entry_gate.py"
    }

    manifest_files = {}
    
    for key, src_path in sources.items():
        if src_path.exists():
            # Copier le fichier dans le registre V712 pour archivage immuable
            dest_path = V712_REGISTRY / src_path.name
            shutil.copy2(src_path, dest_path)
            
            # Calculer le SHA-256
            file_bytes = dest_path.read_bytes()
            file_hash = hashlib.sha256(file_bytes).hexdigest()
            
            manifest_files[key] = {
                "filename": src_path.name,
                "path": str(dest_path.relative_to(ROOT_DIR)).replace("\\", "/"),
                "sha256": file_hash,
                "size_bytes": len(file_bytes)
            }
            print(f"  [OK] Gel et hachage de {src_path.name} -> SHA256: {file_hash[:12]}...")
        else:
            print(f"  [!] Avertissement : Source introuvable pour {key} ({src_path})")

    freeze_manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "governance_version": "V7.12.4-FROZEN",
        "status": "CONTROLLED_GOVERNANCE_SEALED",
        "sealed_artifacts": manifest_files
    }

    manifest_path = V712_REGISTRY / "governance_freeze_manifest.json"
    manifest_path.write_text(json.dumps(freeze_manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    
    build_markdown_summary(freeze_manifest, V712_REGISTRY / "V712_GOVERNANCE_FREEZE_REPORT.md")
    print(f"\n[OK] Sceau de gouvernance établi avec succès dans : {V712_REGISTRY}")

def build_markdown_summary(manifest: dict, md_path: Path):
    lines = [
        "# E-ZZIO V7.12.4 — Governance Freeze Seal Report",
        f"**Date de scellement :** {manifest['timestamp']}",
        f"**Statut du Registre :** `{manifest['status']}`",
        "",
        "## 1. Artefacts de Gouvernance Immuables",
        "| Composant | Fichier | Empreinte SHA-256 | Taille (bytes) |",
        "| :--- | :--- | :--- | :---: |"
    ]

    for key, meta in manifest["sealed_artifacts"].items():
        lines.append(f"| `{key}` | `{meta['filename']}` | `{meta['sha256'][:16]}...` | `{meta['size_bytes']}` |")

    lines.extend([
        "",
        "## 2. Conclusion",
        "La couche de contrôle elle-même est désormais certifiée et versionnée. Toute expansion future en V7.12 s'appuiera sur ce registre immuable comme référence absolue de conformité."
    ])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Rapport Markdown de gel généré : {md_path.name}")

if __name__ == "__main__":
    run_governance_freeze()
