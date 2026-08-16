import os
import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
QUARANTINE_DIR = ROOT_DIR / "runtime" / "audit" / "quarantine"
QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

# Listes d'exclusions permanentes (Zone d'Immunité Absolue)
PERMANENT_EXCLUSIONS = {".env", ".db", ".jsonl", ".sqlite"}
EXCLUDED_PREFIXES = {"config", "registry", "contracts", "kernel"}

def execute_controlled_cleanup(dry_run: bool = True):
    print(f"[*] Démarrage de V7.11.0.9 — Controlled Cleanup Executor (Dry-Run: {dry_run})...")
    
    validation_path = REGISTRY_OUT / "cleanup_validation_result.json"
    if not validation_path.exists():
        print("[!] Erreur : cleanup_validation_result.json introuvable. Exécutez d'abord la V7.11.0.8.")
        return

    validation_data = json.loads(validation_path.read_text(encoding="utf-8"))
    items = validation_data.get("validated_items", [])

    transactions = []
    processed_count = 0
    blocked_count = 0

    for item in items:
        rel_path = item["file"]
        status = item["action_status"]
        
        # 1. Vérification du statut de validation
        if status != "APPROVED":
            blocked_count += 1
            continue

        full_path = ROOT_DIR / rel_path
        if not full_path.exists():
            continue

        # 2. Vérification des exclusions permanentes de sécurité
        if full_path.suffix.lower() in PERMANENT_EXCLUSIONS:
            blocked_count += 1
            continue
        if any(exc in rel_path.lower() for exc in EXCLUDED_PREFIXES):
            blocked_count += 1
            continue

        # 3. Calcul du hash avant action
        try:
            file_hash = hashlib.sha256(full_path.read_bytes()).hexdigest()
        except:
            file_hash = "READ_ERROR"

        # 4. Destination en Quarantaine / Archive structurée
        dest_path = QUARANTINE_DIR / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        transaction_record = {
            "timestamp": datetime.now().isoformat(),
            "source": rel_path,
            "destination": str(dest_path.relative_to(ROOT_DIR)),
            "sha256": file_hash,
            "action": "MOVE_TO_QUARANTINE"
        }

        if not dry_run:
            try:
                shutil.move(str(full_path), str(dest_path))
                transaction_record["status"] = "SUCCESS"
            except Exception as e:
                transaction_record["status"] = f"FAILED: {str(e)}"
        else:
            transaction_record["status"] = "SIMULATED_SUCCESS"

        transactions.append(transaction_record)
        processed_count += 1

    # Enregistrement du journal de transaction
    log_path = REGISTRY_OUT / "cleanup_transaction_log.json"
    log_path.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
        "processed_count": processed_count,
        "blocked_count": blocked_count,
        "transactions": transactions
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    build_markdown_report(processed_count, blocked_count, dry_run, log_path)
    print(f"[OK] V7.11.0.9 Exécuteur terminé. Éléments traités : {processed_count}, Bloqués par sécurité : {blocked_count}")

def build_markdown_report(processed: int, blocked: int, dry_run: bool, log_path: Path):
    md_path = REGISTRY_OUT / "V7_11_0_9_CLEANUP_EXECUTION_REPORT.md"
    lines = [
        "# E-ZZIO V7.11.0.9 — Controlled Cleanup Execution Report",
        f"**Date :** {datetime.now().isoformat()}",
        f"**Mode Simulation (Dry-Run) :** `{dry_run}`",
        "",
        "## 1. Bilan de l'Exécution Transactionnelle",
        f"- **Éléments éligibles et sécurisés traités :** `{processed}`",
        f"- **Éléments rejetés / protégés par les règles d'immunité :** `{blocked}`",
        "",
        "## 2. Garanties de Sécurité Appliquées",
        "- Aucune base de données (`.sqlite`, `.db`) n'a été touchée.",
        "- Aucun fichier de configuration ou journal d'attestation (`.jsonl`) n'a été déplacé.",
        "- Un journal transactionnel complet a été généré pour permettre un éventuel rollback.",
        "",
        f"**Journal enregistré dans :** `{log_path.name}`"
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")

if __name__ == "__main__":
    # Par défaut, exécution en mode Simulation (Dry-Run = True) pour un contrôle visuel absolu.
    # Pour basculer en exécution réelle, passer dry_run=False.
    execute_controlled_cleanup(dry_run=True)
