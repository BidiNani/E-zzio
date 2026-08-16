import os
import ast
import json
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"

def audit_dependency_repair():
    print("[*] Démarrage de V7.11.2.1 — Dependency Repair Audit (Read-Only)...")
    
    target_file = ROOT_DIR / "runtime" / "recovery" / "decision" / "engine.py"
    report = {
        "target_file": str(target_file.relative_to(ROOT_DIR)).replace("\\", "/"),
        "exists": target_file.exists(),
        "import_found": False,
        "analysis": []
    }
    
    if target_file.exists():
        content = target_file.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(content, filename=str(target_file))
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    mod = node.module if isinstance(node, ast.ImportFrom) else ""
                    if not mod and isinstance(node, ast.Import):
                        for n in node.names: mod = n.name
                    
                    if mod and ("quarantine" in mod.lower() or "recovery" in mod.lower()):
                        report["import_found"] = True
                        report["analysis"].append({
                            "module": mod,
                            "lineno": node.lineno,
                            "type": type(node).__name__
                        })
        except Exception as e:
            report["parse_error"] = str(e)

    # Recherche des exécuteurs ou modules de quarantaine actuels dans le dépôt actif
    executors = []
    for path in ROOT_DIR.rglob("*.py"):
        rel = str(path.relative_to(ROOT_DIR)).replace("\\", "/")
        if any(ex in rel.lower() for ex in {"audit", "quarantine", "archive", "legacy", "venv", ".git"}):
            continue
        if "executor" in rel.lower() or "quarantine" in rel.lower() or "rollback" in rel.lower():
            executors.append(rel)

    report["available_active_modules"] = executors

    # Sauvegarde du rapport JSON
    out_json = REGISTRY_OUT / "dependency_repair_audit.json"
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    # Génération du Rapport Markdown
    build_markdown_report(report, out_json)
    print(f"[OK] Audit de réparation généré : {REGISTRY_OUT / 'V7_11_2_1_REPAIR_AUDIT_REPORT.md'}")

def build_markdown_report(report: dict, json_path: Path):
    md_path = REGISTRY_OUT / "V7_11_2_1_REPAIR_AUDIT_REPORT.md"
    lines = [
        "# E-ZZIO V7.11.2.1 — Dependency Repair Audit Report",
        f"**Date :** {datetime.now().isoformat()}",
        f"**Fichier cible analysé :** `{report['target_file']}`",
        f"**Présent sur le disque :** `{report['exists']}`",
        "",
        "## 1. Analyse de l'Import Cible",
    ]

    if report["import_found"]:
        lines.append("⚠️ **Import(s) obsolète(s) ou suspect(s) détecté(s) :**")
        for a in report["analysis"]:
            lines.append(f"- Ligne **{a['lineno']}** : `{a['module']}` (Type: `{a['type']}`)")
    else:
        lines.append("✅ Aucun import direct vers quarantine/recovery trouvé par l'AST (ou syntaxe différente).")

    lines.extend([
        "",
        "## 2. Modules Actifs de Remédiation Disponibles (Alternatives)",
        "Modules d'exécution ou de quarantaine actuellement présents dans le code actif :"
    ])

    for ex in report["available_active_modules"]:
        lines.append(f"- `{ex}`")

    lines.extend([
        "",
        "## 3. Recommandation pour la V7.11.2.2",
        "Avant toute modification, ce rapport confirme la localisation exacte du couplage. Le patch contrôlé (V7.11.2.2) consistera soit à rediriger cet import vers le nouveau module transactionnel validé, soit à purger la dépendance morte si le moteur de décision n'en a plus l'utilité.",
        "",
        f"**Rapport JSON :** `{json_path.name}`"
    ])
    md_path.write_text("\n".join(lines), encoding="utf-8")

if __name__ == "__main__":
    audit_dependency_repair()
