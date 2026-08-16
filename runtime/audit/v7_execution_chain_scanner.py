import os
import sys
import json
import ast
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
OUTPUT_DIR = ROOT_DIR / "runtime" / "audit" / "intelligence_scan"

EXCLUDED_DIRS = {".git", "__pycache__", "venv", "node_modules", "runtime/audit", ".svelte-kit"}

def scan_powershell_references(root_dir: Path) -> dict:
    """Scanne tous les fichiers .ps1 pour détecter les appels à des scripts Python ou endpoints."""
    ps_refs = defaultdict(list)
    for ps_file in root_dir.rglob("*.ps1"):
        if any(ex in ps_file.parts for ex in EXCLUDED_DIRS):
            continue
        try:
            content = ps_file.read_text(encoding="utf-8", errors="replace")
            rel_ps = str(ps_file.relative_to(root_dir)).replace("\\", "/")
            
            # Recherche de mentions de fichiers .py
            matches = re.findall(r'([\w\-\/]+\.py)', content, re.IGNORECASE)
            for m in matches:
                ps_refs[m].append(rel_ps)
                
            # Recherche de mentions de routes API
            route_matches = re.findall(r'/(api/[\w\-/]+|human/[\w\-/]+|maintenance/[\w\-/]+)', content)
            for r in route_matches:
                ps_refs[f"route:{r}"].append(rel_ps)
        except Exception:
            pass
    return ps_refs

def scan_fastapi_mounts(root_dir: Path) -> set:
    """Scanne web_server.py et les routeurs pour trouver les modules montés."""
    mounted_routers = set()
    web_server = root_dir / "web_server.py"
    if web_server.exists():
        try:
            content = web_server.read_text(encoding="utf-8", errors="replace")
            # Extraction des 'from routers import ...' ou 'app.include_router(...)'
            matches = re.findall(r'from\s+routers\s+import\s+([\w\s,]+)', content)
            for m in matches:
                for r in m.split(","):
                    mounted_routers.add(f"routers/{r.strip()}.py")
        except Exception:
            pass
    return mounted_routers

def run_execution_chain_analysis():
    print(f"[*] Analyse forensic des chaînes d'exécution réelles sur {ROOT_DIR}")
    
    ps_references = scan_powershell_references(ROOT_DIR)
    mounted_routers = scan_fastapi_mounts(ROOT_DIR)
    
    inventory_file = OUTPUT_DIR / "inventory_forensic.json"
    dep_graph_file = OUTPUT_DIR / "dependency_graph_forensic.json"

    if not inventory_file.exists() or not dep_graph_file.exists():
        print("[ERR] Rapports de Phase 0 introuvables.")
        return

    inventory = json.loads(inventory_file.read_text(encoding="utf-8"))
    dep_graph = json.loads(dep_graph_file.read_text(encoding="utf-8"))

    matrix = []

    for item in inventory:
        path = item["path"]
        ext = item["extension"]
        
        # Ingestion des données d'importation
        graph_data = dep_graph.get(path, {})
        imported_by = graph_data.get("imported_by", [])
        imports_out = graph_data.get("imports", [])
        
        # Références via PowerShell
        filename = Path(path).name
        ps_calls = ps_references.get(filename, []) + ps_references.get(path, [])
        
        # Est un routeur monté ?
        is_mounted_router = path in mounted_routers or (path.startswith("routers/") and len(ps_calls) > 0)
        
        # Détermination du statut réel
        status = "🟢 ACTIF_CANONIQUE"
        reason = "A des dépendants directs ou est un point d'entrée principal."

        # Re-classification basée sur les données réelles
        if "test_isolation" in path or "microkernel_history" in path or "backup" in path:
            status = "🔵 HISTORIQUE_TEST"
            reason = "Artefact de test, snapshot d'audit ou sauvegarde de version."
        elif is_mounted_router:
            status = "🟢 ACTIF_CANONIQUE"
            reason = "Routeur monté par web_server.py ou appelé via scripts PowerShell."
        elif path in ["web_server.py", "core/ezzio_master.py", "core/pc_commander.py", "core/dispatcher.py"]:
            status = "🟢 ACTIF_CANONIQUE"
            reason = "Point d'entrée système principal."
        elif len(imported_by) == 0 and len(ps_calls) == 0 and ext == ".py":
            if "legacy" in path.lower() or "old" in path.lower():
                status = "🟡 ACTIF_LEGACY"
                reason = "Module legacy sans dépendants directs."
            else:
                status = "🔴 ORPHELIN_REEL"
                reason = "Aucun import entrant, aucun appel PowerShell, non monté dans web_server."

        matrix.append({
            "path": path,
            "domain": item["domain"],
            "status": status,
            "reason": reason,
            "imported_by_count": len(imported_by),
            "imported_by": imported_by[:5],
            "ps_callers": ps_calls,
            "sha256": item["sha256"]
        })

    # Sauvegarde de la matrice
    (OUTPUT_DIR / "REAL_EXECUTION_MATRIX_V7.json").write_text(
        json.dumps(matrix, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Génération du rapport d'exécution Markdown
    build_execution_markdown_report(matrix)

def build_execution_markdown_report(matrix: list):
    status_counts = defaultdict(int)
    for item in matrix:
        status_counts[item["status"]] += 1

    lines = [
        "# E-ZZIO V7 — Matrice d'Analyse d'Exécution Réelle",
        f"**Date :** {datetime.now().isoformat()}",
        f"**Total fichiers classifiés :** {len(matrix)}",
        "",
        "## 1. Bilan par Statut d'Architecture",
        f"- 🟢 **ACTIF_CANONIQUE** : {status_counts['🟢 ACTIF_CANONIQUE']} fichiers",
        f"- 🟡 **ACTIF_LEGACY** : {status_counts['🟡 ACTIF_LEGACY']} fichiers",
        f"- 🔵 **HISTORIQUE_TEST** : {status_counts['🔵 HISTORIQUE_TEST']} fichiers",
        f"- 🔴 **ORPHELIN_REEL** : {status_counts['🔴 ORPHELIN_REEL']} fichiers",
        "",
        "## 2. Liste des Fichiers Identifiés comme 🔴 ORPHELIN_REEL",
        "*(Aucun import Python entrant, aucune référence PowerShell, non monté sur web_server.py)*",
        ""
    ]

    orphans = [m for m in matrix if m["status"] == "🔴 ORPHELIN_REEL"]
    if orphans:
        for o in orphans:
            lines.append(f"- `{o['path']}` (Domaine: {o['domain']})")
    else:
        lines.append("Aucun orphelin réel détecté.")

    lines.extend([
        "",
        "## 3. Cartographie des Routeurs FastAPI",
        ""
    ])

    routers = [m for m in matrix if m['path'].startswith("routers/")]
    for r in routers:
        lines.append(f"- `{r['path']}` -> Statut: {r['status']} (Appels PS: {len(r['ps_callers'])})")

    (OUTPUT_DIR / "ARCHITECTURE_PATHWAYS_V7.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Matrice d'exécution enregistrée dans {OUTPUT_DIR / 'ARCHITECTURE_PATHWAYS_V7.md'}")

if __name__ == "__main__":
    run_execution_chain_analysis()
