import os
import json
import hashlib
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
REGISTRY_OUT.mkdir(parents=True, exist_ok=True)

def validate_cleanup_plan():
    print("[*] Démarrage de V7.11.0.8 — Cleanup Validator & Risk Assessment...")
    
    # 1. Charger la baseline pour retrouver les listes
    baseline_path = REGISTRY_OUT / "architecture_baseline.json"
    if not baseline_path.exists():
        print("[!] Erreur : architecture_baseline.json introuvable. Exécutez d'abord la V7.11.0.6.")
        return

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    
    # 2. Recréer/Déplacer le manifeste au bon endroit dans V7_REGISTRY
    plan = {
        "move_to_archive": baseline.get("ARCHIVE", []),
        "move_to_legacy": baseline.get("LEGACY", []),
        "move_to_temp": baseline.get("TEMPORARY", [])
    }
    plan_path = REGISTRY_OUT / "V7_11_0_7_CLEANUP_PLAN.json"
    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")

    # 3. Analyser et valider chaque fichier du plan
    validated_items = []
    
    for category, files in plan.items():
        for rel_file in files:
            full_path = ROOT_DIR / rel_file
            exists = full_path.exists()
            size = full_path.stat().st_size if exists else 0
            file_hash = "N/A"
            
            # Évaluation des risques
            risk = "LOW"
            action_allowed = "APPROVED"
            
            if not exists:
                risk = "NONE"
                action_allowed = "SKIPPED_NOT_FOUND"
            elif full_path.suffix.lower() in {".db", ".jsonl", ".env"} or "config" in rel_file.lower():
                risk = "HIGH"
                action_allowed = "BLOCKED_SENSITIVE_DATA"
            elif category == "move_to_temp" and ("__pycache__" in rel_file or full_path.suffix == ".pyc"):
                risk = "LOW"
                action_allowed = "APPROVED"
            elif category == "move_to_temp":
                risk = "MEDIUM"
                action_allowed = "REQUIRES_REVIEW"
            
            if exists and risk != "HIGH":
                try:
                    file_hash = hashlib.sha256(full_path.read_bytes()).hexdigest()[:16] + "..."
                except:
                    file_hash = "READ_ERROR"

            validated_items.append({
                "file": rel_file,
                "category": category,
                "exists": exists,
                "size_bytes": size,
                "sha256_prefix": file_hash,
                "risk": risk,
                "action_status": action_allowed
            })

    report_payload = {
        "timestamp": datetime.now().isoformat(),
        "total_evaluated": len(validated_items),
        "validated_items": validated_items
    }

    # Sauvegarde du rapport JSON
    out_json = REGISTRY_OUT / "cleanup_validation_result.json"
    out_json.write_text(json.dumps(report_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # Génération du Rapport Markdown
    build_markdown(report_payload)
    print(f"[OK] V7.11.0.8 Cleanup Validator terminé. Rapport : {REGISTRY_OUT / 'V7_11_0_8_CLEANUP_VALIDATION_REPORT.md'}")

def build_markdown(payload: dict):
    md_path = REGISTRY_OUT / "V7_11_0_8_CLEANUP_VALIDATION_REPORT.md"
    items = payload.get("validated_items", [])
    
    blocked = [i for i in items if "BLOCKED" in i["action_status"]]
    review = [i for i in items if "REVIEW" in i["action_status"]]
    approved = [i for i in items if "APPROVED" in i["action_status"]]

    lines = [
        "# E-ZZIO V7.11.0.8 — Cleanup Validation & Risk Report",
        f"**Date :** {payload.get('timestamp')}",
        f"**Total Évalué :** {payload.get('total_evaluated')} fichiers",
        "",
        "## 1. Résumé des Risques de Nettoyage",
        f"- 🟢 **Approuvés (Prêts pour action) :** {len(approved)}",
        f"- 🟡 **Nécessitant une révision (Requires Review) :** {len(review)}",
        f"- 🔴 **Bloqués (Protégés / Sensibles) :** {len(blocked)}",
        "",
        "## 2. Éléments Bloqués (Sécurité Prioritaire)",
        "Ces fichiers ont été identifiés dans le plan de nettoyage mais présentent un risque critique (bases de données, logs, configurations ou environnements) :"
    ]

    for b in blocked[:15]: # Limiter l'affichage pour la lisibilité
        lines.append(f"- `[HIGH RISK]` **{b['file']}** ({b['category']}) -> **{b['action_status']}**")

    if len(blocked) > 15:
        lines.append(f"- *... et {len(blocked) - 15} autres fichiers bloqués.*")

    lines.extend([
        "",
        "## 3. Conclusion de l'Étape V7.11.0.8",
        "Le validateur a intercepté les risques potentiels (bases de données ou fichiers de configuration) qui figuraient par erreur dans les listes de nettoyage brut. Aucun fichier critique ne sera supprimé ou déplacé sans validation formelle.",
        "",
        "**Prochaine étape autorisée :** Affinement du plan ou passage à la V7.11.0.9 (Controlled Executor restreint aux éléments `APPROVED`)."
    ])

    md_path.write_text("\n".join(lines), encoding="utf-8")

if __name__ == "__main__":
    validate_cleanup_plan()
