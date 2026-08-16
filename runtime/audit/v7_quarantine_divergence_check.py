import os
import json
import hashlib
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
QUARANTINE_DIR = ROOT_DIR / "runtime" / "quarantine" / "V7.11.1.1"

def check_divergence():
    print("[*] Démarrage de V7.11.2.6 — Quarantine Divergence Check...")
    
    if not QUARANTINE_DIR.exists():
        print("[!] Aucun dossier de quarantaine actif trouvé. Nettoyage physique non exécuté.")
        return

    divergence_results = []
    stats = {"SAME_HASH": 0, "ACTIVE_DIFFERS": 0, "QUARANTINE_ONLY_SURVIVOR": 0}

    # Parcourir tous les fichiers de la quarantaine
    for q_file in QUARANTINE_DIR.rglob("*"):
        if not q_file.is_file():
            continue

        # Calculer le chemin relatif par rapport à la racine de quarantaine
        try:
            rel_path = q_file.relative_to(QUARANTINE_DIR)
        except:
            continue

        active_file = ROOT_DIR / rel_path
        
        q_hash = "READ_ERROR"
        try:
            q_hash = hashlib.sha256(q_file.read_bytes()).hexdigest()
        except:
            pass

        entry = {
            "file": str(rel_path).replace("\\", "/"),
            "quarantine_sha256": q_hash,
            "active_exists": active_file.exists(),
            "status": "UNKNOWN"
        }

        if active_file.exists():
            try:
                a_hash = hashlib.sha256(active_file.read_bytes()).hexdigest()
                entry["active_sha256"] = a_hash
                if q_hash == a_hash:
                    entry["status"] = "SAME_HASH"
                    stats["SAME_HASH"] += 1
                else:
                    entry["status"] = "ACTIVE_DIFFERS"
                    stats["ACTIVE_DIFFERS"] += 1
            except:
                entry["status"] = "ACTIVE_READ_ERROR"
        else:
            entry["status"] = "QUARANTINE_ONLY_SURVIVOR"
            stats["QUARANTINE_ONLY_SURVIVOR"] += 1

        divergence_results.append(entry)

    report = {
        "timestamp": datetime.now().isoformat(),
        "total_quarantined_files_checked": len(divergence_results),
        "statistics": stats,
        "divergence_details": divergence_results
    }

    out_json = REGISTRY_OUT / "quarantine_divergence_report.json"
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    build_markdown_report(report, out_json)
    print(f"[OK] Audit de divergence terminé. Rapport : {REGISTRY_OUT / 'V7_11_2_6_DIVERGENCE_REPORT.md'}")

def build_markdown_report(report: dict, json_path: Path):
    md_path = REGISTRY_OUT / "V7_11_2_6_DIVERGENCE_REPORT.md"
    stats = report["statistics"]
    lines = [
        "# E-ZZIO V7.11.2.6 — Quarantine Divergence Audit Report",
        f"**Date :** {report['timestamp']}",
        f"**Total fichiers de quarantaine audités :** `{report['total_quarantined_files_checked']}`",
        "",
        "## 1. Synthèse des États de Divergence",
        f"- 🟢 **Même empreinte (SAME_HASH) :** `{stats['SAME_HASH']}`",
        f"- 🟡 **Actif différent (ACTIVE_DIFFERS) :** `{stats['ACTIVE_DIFFERS']}`",
        f"- 🔵 **Présents uniquement en quarantaine (Obsolètes purs) :** `{stats['QUARANTINE_ONLY_SURVIVOR']}`",
        "",
        "## 2. Interprétation Architecturale",
        "Cet audit compare l'état capturé au moment du nettoyage transactionnel avec l'état actuel du dépôt. S'il n'y a pas de divergence critique sur les modules de décision, la phase V7.11.2 peut être officiellement certifiée.",
        "",
        f"**Rapport JSON :** `{json_path.name}`"
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")

if __name__ == "__main__":
    check_divergence()
