"""
E-ZZIO V7.61.2 — Full Integration Forensic Audit
Vérifie la syntaxe, les imports, l'exposition des points legacy et l'intégrité 
du registre budgétaire en mode lecture seule (Correction syntaxique).
"""
import os
import ast
import json
import re
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(r"G:\AI\E-zzio")
CORE_COG_DIR = ROOT_DIR / "core" / "cognition"
OUTPUT_REPORT = ROOT_DIR / "runtime" / "audit" / "system" / "ecol_deep_forensic_audit_report.json"

def audit_syntax_and_imports():
    print("[*] Étape 1/4 : Vérification de la syntaxe et des imports des modules ECOL...")
    module_status = {}
    
    if not CORE_COG_DIR.exists():
        return {"error": "Répertoire core/cognition introuvable."}

    for path in CORE_COG_DIR.glob("*.py"):
        mod_name = path.name
        try:
            with open(path, "r", encoding="utf-8") as f:
                code_content = f.read()
            
            ast.parse(code_content, filename=str(path))
            
            imports = []
            tree = ast.parse(code_content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module_str = node.module if node.module else ""
                    imports.append(module_str)

            module_status[mod_name] = {
                "syntax_valid": True,
                "imports": list(set(imports)),
                "size_bytes": path.stat().st_size
            }
        except Exception as e:
            module_status[mod_name] = {
                "syntax_valid": False,
                "error": str(e)
            }
            
    return module_status

def audit_legacy_bypasses():
    print("[*] Étape 2/4 : Cartographie des contournements potentiels (Appels directs hors ECOL)...")
    bypasses = []
    forbidden_patterns = [r"\bimport\s+ollama\b", r"\bimport\s+openai\b", r"\bclient\.chat\b", r"\brequests\.post\b"]

    for target_dir in ["core", "runtime"]:
        dir_path = ROOT_DIR / target_dir
        if not dir_path.exists():
            continue

        for path in dir_path.rglob("*.py"):
            rel_path = path.relative_to(ROOT_DIR).as_posix()
            if ".venv" in rel_path or "__pycache__" in rel_path or "cognition" in rel_path:
                continue

            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                for pattern in forbidden_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        bypasses.append({
                            "file": rel_path,
                            "trigger": pattern
                        })
            except Exception:
                continue

    return bypasses

def audit_ledger_integrity():
    print("[*] Étape 3/4 : Audit de la structure et de l'intégrité du Token Ledger...")
    ledger_path = ROOT_DIR / "runtime" / "cognition" / "budget" / "cognitive_budget_ledger.jsonl"
    
    if not ledger_path.exists():
        return {"status": "MISSING", "message": "Le registre budgétaire n'a pas encore été initialisé."}

    records_count = 0
    valid_format = True
    try:
        with open(ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records_count += 1
                    json.loads(line)
    except Exception:
        valid_format = False

    return {
        "status": "EXISTS",
        "records_count": records_count,
        "json_format_valid": valid_format,
        "chained_hash_implemented": False
    }

def run_forensic_audit():
    syntax_results = audit_syntax_and_imports()
    bypass_results = audit_legacy_bypasses()
    ledger_results = audit_ledger_integrity()

    report = {
        "audit_timestamp": datetime.now(timezone.utc).isoformat(),
        "modules_health": syntax_results,
        "unrouted_legacy_calls": bypass_results,
        "ledger_audit": ledger_results,
        "governance_status": "PENDING_CHAINED_HASH_UPGRADE"
    }

    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 65)
    print(" ECOL DEEP FORENSIC AUDIT REPORT (V7.61.2)")
    print("=" * 65)
    print(f" Modules ECOL audités : {len(syntax_results)}")
    print(f" Points d'appel directs (Bypasses potentiels) : {len(bypass_results)}")
    print(f" Statut du Token Ledger : {ledger_results.get('status')} ({ledger_results.get('records_count', 0)} enregistrements)")
    print("-" * 65)
    if bypass_results:
        print(" [!] Attention : Des modules parlent encore directement aux fournisseurs :")
        for b in bypass_results[:5]:
            print(f"     - {b['file']} (Trigger: {b['trigger']})")
    else:
        print(" [OK] Aucun appel direct brut détecté dans le périmètre analysé.")
    print("=" * 65)
    print(f" Rapport forensic exporté : {OUTPUT_REPORT}")

if __name__ == "__main__":
    run_forensic_audit()
