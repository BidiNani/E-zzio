import os
import sys
import json
import ast
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
REGISTRY_OUT.mkdir(parents=True, exist_ok=True)

TARGET_FILES = [
    "runtime/hardware/trust/models/registry.py",
    "runtime/hardware/trust/models/contract_signer.py",
    "runtime/hardware/trust/execution/attestation/verifier.py"
]

def inspect_file_semantics(file_path: Path) -> dict:
    if not file_path.exists():
        return {"exists": False}
        
    content = file_path.read_text(encoding="utf-8", errors="replace")
    
    analysis = {
        "exists": True,
        "lines": len(content.splitlines()),
        "loads_contracts": ".contract.json" in content or "contract" in content.lower(),
        "uses_hmac": "hmac" in content.lower(),
        "uses_sha256": "sha256" in content.lower(),
        "uses_concat_hashing": "secret" in content.lower() and "+" in content,
        "functions": [],
        "classes": []
    }

    try:
        tree = ast.parse(content, filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                analysis["functions"].append(node.name)
            elif isinstance(node, ast.ClassDef):
                analysis["classes"].append(node.name)
    except Exception as e:
        analysis["ast_error"] = str(e)

    return analysis

def run_trust_audit():
    print("[*] Démarrage de l'audit de consolidation de confiance V7.7...")
    results = {}

    for rel_path in TARGET_FILES:
        full_path = ROOT_DIR / rel_path
        results[rel_path] = inspect_file_semantics(full_path)

    payload = {
        "timestamp": datetime.now().isoformat(),
        "trust_components_audit": results
    }

    out_json = REGISTRY_OUT / "trust_consolidation_audit.json"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    build_markdown(results)
    print(f"[OK] Audit V7.7 terminé. Rapports générés dans {REGISTRY_OUT}")

def build_markdown(results: dict):
    md_path = REGISTRY_OUT / "V7.7_TRUST_CONSOLIDATION_REPORT.md"
    lines = [
        "# E-ZZIO V7.7 — Rapport d'Audit de Consolidation de l'Autorité de Confiance",
        f"**Date :** {datetime.now().isoformat()}",
        "",
        "## Analyse des Composants Clés de la Trust Layer",
        ""
    ]

    for path, data in results.items():
        lines.append(f"### Fichier : `{path}`")
        if not data.get("exists"):
            lines.append("- **Statut :** `INTROUVABLE SUR LE DISQUE`")
            lines.append("")
            continue
            
        lines.extend([
            f"- **Lignes de code :** `{data.get('lines')}`",
            f"- **Charge des contrats :** `{data.get('loads_contracts')}`",
            f"- **Utilise HMAC :** `{data.get('uses_hmac')}`",
            f"- **Utilise SHA256 :** `{data.get('uses_sha256')}`",
            f"- **Indices de hachage concaténé (Secret+Payload) :** `{data.get('uses_concat_hashing')}`",
            f"- **Classes définies :** `{data.get('classes')}`",
            f"- **Fonctions définies :** `{data.get('functions')}`",
            ""
        ])

    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Rapport Markdown généré : {md_path}")

if __name__ == "__main__":
    run_trust_audit()
