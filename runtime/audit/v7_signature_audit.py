import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
REGISTRY_OUT.mkdir(parents=True, exist_ok=True)

def audit_signatures():
    print("[*] Audit forensic des mécanismes de signature et de vérification...")
    findings = []
    
    # Patterns de recherche cryptographique et d'intégrité
    crypto_patterns = re.compile(r'\b(hmac|sha256|sign|verify|secret_key|public_key|Signer|Verifier|verify_signature|hashlib)\b', re.IGNORECASE)

    for py_file in ROOT_DIR.rglob("*.py"):
        rel_parts = py_file.relative_to(ROOT_DIR).parts
        if any(ex in rel_parts for ex in {".git", "__pycache__", "venv", "node_modules", "runtime/audit"}):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            matches = crypto_patterns.findall(content)
            if matches:
                rel_path = str(py_file.relative_to(ROOT_DIR)).replace("\\", "/")
                matching_lines = [line.strip() for line in content.splitlines() if crypto_patterns.search(line)]
                findings.append({
                    "path": rel_path,
                    "unique_matches": list(set(matches)),
                    "matching_lines": matching_lines[:4]  # Limité pour la lisibilité
                })
        except Exception:
            pass
            
    return findings

def run_signature_audit():
    findings = audit_signatures()
    
    payload = {
        "timestamp": datetime.now().isoformat(),
        "total_files_with_crypto_patterns": len(findings),
        "signature_authority_findings": findings
    }
    
    out_json = REGISTRY_OUT / "signature_audit_results.json"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    
    build_markdown(findings)
    print(f"[OK] Audit V7.6 terminé. Rapports générés dans {REGISTRY_OUT}")

def build_markdown(findings):
    md_path = REGISTRY_OUT / "V7_SIGNATURE_AUTHORITY_REPORT.md"
    lines = [
        "# E-ZZIO V7.6 — Rapport d'Audit de l'Autorité de Signature",
        f"**Date :** {datetime.now().isoformat()}",
        f"**Fichiers présentant des patterns cryptographiques :** {len(findings)}",
        "",
        "## Fichiers Identifiés",
        ""
    ]
    
    for f in findings:
        lines.append(f"### Fichier : `{f['path']}`")
        lines.append(f"- **Mots-clés :** `{f['unique_matches']}`")
        lines.append("- **Contexte extrait :**")
        for line in f['matching_lines']:
            lines.append(f"  - `{line}`")
        lines.append("")
        
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Rapport Markdown généré : {md_path}")

if __name__ == "__main__":
    run_signature_audit()
