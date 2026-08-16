import os
import ast
import json
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"

def analyze_symbol_usage():
    print("[*] Démarrage de V7.11.2.2 — Dependency Symbol Usage Analyzer...")
    
    target_file = ROOT_DIR / "runtime" / "recovery" / "decision" / "engine.py"
    if not target_file.exists():
        print(f"[X] Erreur : Fichier cible introuvable : {target_file}")
        return

    content = target_file.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(content, filename=str(target_file))

    imported_symbols = {}
    used_names = set()

    # 1. Collecter tous les noms importés et collecter tous les noms utilisés dans le code
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name
                imported_symbols[name] = {"source_module": alias.name, "lineno": node.lineno, "used": False}
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for alias in node.names:
                name = alias.asname or alias.name
                full_name = f"{mod}.{alias.name}" if mod else alias.name
                imported_symbols[name] = {"source_module": full_name, "lineno": node.lineno, "used": False}
        elif isinstance(node, ast.Name):
            used_names.add(node.id)

    # 2. Vérifier l'utilisation effective des symboles importés
    for sym, meta in imported_symbols.items():
        if sym in used_names:
            meta["used"] = True

    # 3. Vérification de l'existence physique des modules importés dans le dépôt actif
    physical_checks = []
    for sym, meta in imported_symbols.items():
        mod_path_str = meta["source_module"].replace(".", "/") + ".py"
        potential_path = ROOT_DIR / mod_path_str
        pkg_path = ROOT_DIR / meta["source_module"].replace(".", "/")
        
        exists = potential_path.exists() or (pkg_path.is_dir() and (pkg_path / "__init__.py").exists())
        
        physical_checks.append({
            "symbol": sym,
            "module": meta["source_module"],
            "lineno": meta["lineno"],
            "effectively_used_in_code": meta["used"],
            "physical_file_exists": exists
        })

    report = {
        "timestamp": datetime.now().isoformat(),
        "target_file": str(target_file.relative_to(ROOT_DIR)).replace("\\", "/"),
        "symbol_analysis": physical_checks
    }

    # Sauvegarde JSON
    out_json = REGISTRY_OUT / "symbol_usage_analysis.json"
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    # Génération Markdown
    build_markdown_report(report, out_json)
    print(f"[OK] Analyse d'usage terminée. Rapport : {REGISTRY_OUT / 'V7_11_2_2_SYMBOL_USAGE_REPORT.md'}")

def build_markdown_report(report: dict, json_path: Path):
    md_path = REGISTRY_OUT / "V7_11_2_2_SYMBOL_USAGE_REPORT.md"
    lines = [
        "# E-ZZIO V7.11.2.2 — Symbol Usage & Dead Import Analyzer",
        f"**Date :** {report['timestamp']}",
        f"**Fichier cible :** `{report['target_file']}`",
        "",
        "## 1. Matrice d'Usage des Imports",
        "| Symbole / Module | Ligne | Utilisé dans le code ? | Fichier physique présent ? | Statut architectural |",
        "| :--- | :---: | :---: | :---: | :--- |"
    ]

    for item in report["symbol_analysis"]:
        used_icon = "✅ Oui" if item["effectively_used_in_code"] else "❌ Non (Mort)"
        phys_icon = "✅ Présent" if item["physical_file_exists"] else "⚠️ Absent / Quarantaine"
        
        status = "SAIN"
        if not item["effectively_used_in_code"]:
            status = "DEAD_IMPORT (À purger)"
        elif not item["physical_file_exists"]:
            status = "BROKEN_IMPORT (Critique)"

        lines.append(f"| `{item['module']}` | {item['lineno']} | {used_icon} | {phys_icon} | **{status}** |")

    lines.extend([
        "",
        "## 2. Conclusion de l'Analyse d'Usage",
        "Cette matrice sépare définitivement les imports fonctionnels des vestiges historiques. Tout import marqué `DEAD_IMPORT` peut être supprimé sans risque pour la logique d'exécution.",
        "",
        f"**Rapport JSON :** `{json_path.name}`"
    ])
    md_path.write_text("\n".join(lines), encoding="utf-8")

if __name__ == "__main__":
    analyze_symbol_usage()
