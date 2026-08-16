import os
import json
import hashlib
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
REGISTRY_OUT.mkdir(parents=True, exist_ok=True)

def discover_quarantine():
    print("[*] Démarrage de V7.11.2.6-BIS — Quarantine Discovery Audit...")
    
    # Recherche dynamique de tout dossier contenant 'quarantine' dans le dépôt
    quarantine_candidates = []
    for p in ROOT_DIR.rglob("*"):
        if p.is_dir() and "quarantine" in p.name.lower():
            quarantine_candidates.append(p)
    
    # Filtrer pour écarter les faux positifs (ex: fichiers de configuration d'audit)
    valid_quarantines = [q for q in quarantine_candidates if "audit" not in str(q).lower() or "quarantine" in q.name.lower()]
    
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "candidates_found": [str(c.relative_to(ROOT_DIR)).replace("\\", "/") for c in valid_quarantines],
        "audit_results": [],
        "status": "NO_QUARANTINE_FOUND"
    }

    if not valid_quarantines:
        print("[!] Aucun répertoire de quarantaine physique détecté sur le dépôt.")
    else:
        report_data["status"] = "QUARANTINE_LOCATED"
        print(f"[*] {len(valid_quarantines)} conteneur(s) de quarantaine identifié(s). Analyse...")
        
        for q_dir in valid_quarantines:
            for q_file in q_dir.rglob("*"):
                if not q_file.is_file(): 
                    continue
                try:
                    rel_path = q_file.relative_to(q_dir)
                except:
                    continue
                
                active_file = ROOT_DIR / rel_path
                q_hash = hashlib.sha256(q_file.read_bytes()).hexdigest()
                active_exists = active_file.exists()
                
                status = "QUARANTINE_ONLY"
                a_hash = "N/A"
                if active_exists:
                    a_hash = hashlib.sha256(active_file.read_bytes()).hexdigest()
                    status = "SAME_HASH" if q_hash == a_hash else "ACTIVE_DIFFERS"

                report_data["audit_results"].append({
                    "quarantine_dir": str(q_dir.relative_to(ROOT_DIR)).replace("\\", "/"),
                    "file": str(rel_path).replace("\\", "/"),
                    "quarantine_sha256": q_hash,
                    "active_exists": active_exists,
                    "active_sha256": a_hash,
                    "comparison_status": status
                })

    out_json = REGISTRY_OUT / "quarantine_discovery_report.json"
    out_json.write_text(json.dumps(report_data, indent=2, ensure_ascii=False), encoding="utf-8")

    build_markdown(report_data, out_json)
    print(f"[OK] Audit de découverte terminé. Rapport : {REGISTRY_OUT / 'V7_11_2_6_BIS_DISCOVERY_REPORT.md'}")

def build_markdown(payload: dict, json_path: Path):
    md_path = REGISTRY_OUT / "V7_11_2_6_BIS_DISCOVERY_REPORT.md"
    lines = [
        "# E-ZZIO V7.11.2.6-BIS — Quarantine Discovery & Divergence Report",
        f"**Date :** {payload['timestamp']}",
        f"**Statut de la recherche :** `{payload['status']}`",
        f"**Dossiers de quarantaine identifiés :** `{len(payload['candidates_found'])}`",
        ""
    ]
    
    if payload['candidates_found']:
        lines.append("### Chemins détectés :")
        for c in payload['candidates_found']:
            lines.append(f"- `{c}`")
    else:
        lines.append("ℹ️ *Aucun dossier de quarantaine physique n'a été trouvé (ce qui confirme que le dépôt n'a pas encore subi de mutation physique active ou que la quarantaine a été purgée).*")

    lines.extend([
        "",
        "## Synthèse d'Analyse",
        f"- **Total fichiers analysés :** `{len(payload['audit_results'])}`",
        "",
        f"**Rapport JSON :** `{json_path.name}`"
    ])
    md_path.write_text("\n".join(lines), encoding="utf-8")

if __name__ == "__main__":
    discover_quarantine()
