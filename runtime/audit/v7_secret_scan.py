import os
import json
import re
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
REGISTRY_OUT.mkdir(parents=True, exist_ok=True)

# Regex Patterns pour détection de secrets
PATTERNS = {
    "Generic_API_Key": r"(?i)(api_key|token|password|secret)\s*[:=]\s*['\"]?[a-zA-Z0-9_\-\.]{15,}['\"]?",
    "GitHub_Token": r"ghp_[a-zA-Z0-9]{36}",
    "OpenAI_Key": r"sk-[a-zA-Z0-9]{32,}",
    "AWS_Key": r"AKIA[0-9A-Z]{16}",
    "Discord_Token": r"[a-zA-Z0-9_-]{24}\.[a-zA-Z0-9_-]{6}\.[a-zA-Z0-9_-]{27}"
}

def scan_secrets():
    print("[*] Démarrage du Secret & Credential Forensic Scan...")
    findings = []
    
    for file_path in ROOT_DIR.rglob("*.*"):
        rel_parts = file_path.relative_to(ROOT_DIR).parts
        # Exclusion des dossiers non pertinents
        if any(ex in rel_parts for ex in {".git", "__pycache__", "venv", "node_modules", "runtime/audit"}):
            continue
        if file_path.suffix.lower() in {".png", ".jpg", ".exe", ".bin", ".pyc"}:
            continue
            
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            for name, pattern in PATTERNS.items():
                for match in re.finditer(pattern, content):
                    findings.append({
                        "file": str(file_path.relative_to(ROOT_DIR)).replace("\\", "/"),
                        "pattern": name,
                        "context": match.group(0)[:50] # Preview tronquée pour sécurité
                    })
        except Exception:
            pass
            
    return findings

def run_scan():
    findings = scan_secrets()
    payload = {
        "timestamp": datetime.now().isoformat(),
        "total_findings": len(findings),
        "findings": findings
    }
    
    (REGISTRY_OUT / "secret_forensic_results.json").write_text(json.dumps(payload, indent=2))
    
    # Rapport Markdown
    md_path = REGISTRY_OUT / "V7_11_0_3_SECRET_FORENSIC_REPORT.md"
    lines = ["# E-ZZIO V7.11.0.3 — Secret & Credential Forensic Scan", f"**Date :** {payload['timestamp']}", ""]
    
    if not findings:
        lines.append("## ✅ Aucune clé API ou token majeur détecté via pattern standard.")
    else:
        lines.append(f"## ⚠️ {len(findings)} potentiel(s) secret(s) détecté(s)")
        for f in findings:
            lines.append(f"- **Fichier :** `{f['file']}` | **Type :** `{f['pattern']}` | **Aperçu :** `{f['context']}`")
    
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Audit de secrets terminé. Rapport : {md_path}")

if __name__ == "__main__":
    run_scan()
