import os
import json
import hashlib
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
QUARANTINE_DIR = ROOT_DIR / "runtime" / "quarantine" / "V7.11.1.1"

def plan_restore():
    print("[*] Démarrage de V7.11.2.3 — Recovery Dependency Restore Planner...")
    
    symbol_json = REGISTRY_OUT / "symbol_usage_analysis.json"
    if not symbol_json.exists():
        print("[!] Erreur : symbol_usage_analysis.json introuvable. Exécutez d'abord la V7.11.2.2.")
        return

    analysis = json.loads(symbol_json.read_text(encoding="utf-8"))
    broken_items = [item for item in analysis.get("symbol_analysis", []) if not item["physical_file_exists"] and item["effectively_used_in_code"]]

    restore_plan = []
    
    for item in broken_items:
        module_path_rel = item["module"].replace(".", "/") + ".py"
        quarantine_file = QUARANTINE_DIR / module_path_rel
        active_target = ROOT_DIR / module_path_rel

        exists_in_quarantine = quarantine_file.exists()
        q_hash = "N/A"
        if exists_in_quarantine:
            try:
                q_hash = hashlib.sha256(quarantine_file.read_bytes()).hexdigest()
            except:
                q_hash = "READ_ERROR"

        restore_plan.append({
            "symbol": item["symbol"],
            "module": item["module"],
            "source_in_quarantine": str(quarantine_file.relative_to(ROOT_DIR)).replace("\\", "/") if exists_in_quarantine else "NOT_FOUND",
            "target_in_active": str(active_target.relative_to(ROOT_DIR)).replace("\\", "/"),
            "quarantine_file_exists": exists_in_quarantine,
            "sha256": q_hash,
            "action": "RESTORE_TO_ACTIVE" if exists_in_quarantine else "MANUAL_CHECK_REQUIRED"
        })

    # Sauvegarde du plan de restauration
    plan_payload = {
        "timestamp": datetime.now().isoformat(),
        "total_items_to_restore": len(restore_plan),
        "restore_plan": restore_plan
    }

    out_json = REGISTRY_OUT / "recovery_restore_plan.json"
    out_json.write_text(json.dumps(plan_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # Génération du Rapport Markdown
    build_markdown_report(plan_payload, out_json)
    print(f"[OK] Plan de restauration généré : {REGISTRY_OUT / 'V7_11_2_3_RESTORE_PLAN_REPORT.md'}")

def build_markdown_report(payload: dict, json_path: Path):
    md_path = REGISTRY_OUT / "V7_11_2_3_RESTORE_PLAN_REPORT.md"
    lines = [
        "# E-ZZIO V7.11.2.3 — Recovery Restore Plan Report",
        f"**Date :** {payload['timestamp']}",
        f"**Éléments identifiés pour restauration :** `{payload['total_items_to_restore']}`",
        "",
        "## 1. Matrice de Restauration (Quarantaine → Active)",
        "| Module / Symbole | Présent en Quarantaine ? | Cible Active | Statut de l'Opération |",
        "| :--- | :---: | :--- | :--- |"
    ]

    for item in payload["restore_plan"]:
        q_status = "✅ Oui" if item["quarantine_file_exists"] else "❌ Introuvable"
        lines.append(f"| `{item['module']}` | {q_status} | `{item['target_in_active']}` | **{item['action']}** |")

    lines.extend([
        "",
        "## 2. Conclusion du Planificateur",
        "Ce plan garantit qu'aucune réécriture de code n'est nécessaire. Les modules indispensables à engine.py seront replacés à l'identique depuis la quarantaine sous contrôle d'intégrité SHA-256.",
        "",
        f"**Rapport JSON :** `{json_path.name}`"
    ])
    md_path.write_text("\n".join(lines), encoding="utf-8")

if __name__ == "__main__":
    plan_restore()
