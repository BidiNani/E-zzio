import os
import sys
import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
QUARANTINE_ROOT = ROOT_DIR / "runtime" / "quarantine" / "V7.11.1.2"

IMMUNE_EXTENSIONS = {".env", ".sqlite", ".db", ".jsonl"}
IMMUNE_PREFIXES = (
    "runtime/contracts",
    "runtime/kernel",
    "runtime/security",
    "runtime/recovery",
    "registry"
)

def normalize_relative_path(rel_path: str) -> str:
    """Nettoie les chemins redondants ou pollués par des préfixes absolus/relatifs (ex: AI/E-zzio)."""
    p = Path(rel_path)
    parts = list(p.parts)
    while "AI" in parts:
        idx = parts.index("AI")
        if idx + 1 < len(parts) and parts[idx+1] == "E-zzio":
            parts = parts[idx+2:]
            break
    return str(Path(*parts)).replace("\\", "/")

def is_absolutely_immune(rel_path: str) -> bool:
    normalized = normalize_relative_path(rel_path)
    p = Path(normalized)
    
    if p.suffix.lower() in IMMUNE_EXTENSIONS or ".env" in p.name.lower():
        return True
    
    rel_lower = normalized.replace("\\", "/").lower()
    for prefix in IMMUNE_PREFIXES:
        if rel_lower.startswith(prefix) or f"/{prefix}" in rel_lower:
            return True
    return False

def check_quarantine_space(required_bytes: int) -> bool:
    try:
        QUARANTINE_ROOT.mkdir(parents=True, exist_ok=True)
        stat = shutil.disk_usage(QUARANTINE_ROOT)
        return stat.free >= int(required_bytes * 1.20)
    except Exception:
        return True

def append_tx_log(log_path: Path, entry: dict):
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def run_executor():
    execute_mode = "--execute" in sys.argv
    mode_label = "EXECUTE (MUTATION ACTIVE)" if execute_mode else "DRY-RUN (SIMULATION)"
    print(f"[*] Démarrage de V7.11.1.2 Normalized Executor (Mode: {mode_label})")

    manifest_path = REGISTRY_OUT / "cleanup_approval_manifest.json"
    if not manifest_path.exists():
        print("[X] ABORT : cleanup_approval_manifest.json introuvable.")
        sys.exit(1)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = manifest.get("items", [])

    print(f"[*] Analyse du Pre-flight Gate & Normalisation pour {len(items)} entrées...")

    verified_items = []
    blocked_reconciliation = []
    total_bytes_to_move = 0

    for item in items:
        raw_rel_path = item["file"]
        norm_rel_path = normalize_relative_path(raw_rel_path)
        
        # 1. Contrôle Immunité sur chemin normalisé
        if is_absolutely_immune(norm_rel_path):
            blocked_reconciliation.append({
                "file": raw_rel_path,
                "normalized_file": norm_rel_path,
                "reason": "IMMUNITY_RULE_VIOLATION",
                "timestamp": datetime.now().isoformat()
            })
            continue

        full_path = ROOT_DIR / norm_rel_path
        if not full_path.exists():
            # Fallback sur le chemin brut si le normalisé échoue
            full_path = ROOT_DIR / raw_rel_path
            if not full_path.exists():
                blocked_reconciliation.append({
                    "file": raw_rel_path,
                    "reason": "FILE_MISSING_ON_DISK",
                    "timestamp": datetime.now().isoformat()
                })
                continue

        try:
            file_size = full_path.stat().st_size
            current_hash = hashlib.sha256(full_path.read_bytes()).hexdigest()
            
            if item["sha256_before"] != "READ_ERROR" and current_hash != item["sha256_before"]:
                blocked_reconciliation.append({
                    "file": raw_rel_path,
                    "reason": "HASH_MISMATCH_MODIFIED_AFTER_APPROVAL",
                    "expected_sha256": item.get("sha256_before"),
                    "current_sha256": current_hash,
                    "timestamp": datetime.now().isoformat()
                })
                continue
            
            verified_items.append({
                "source_path": full_path,
                "rel_path": norm_rel_path,
                "category": item.get("destination", "TEMPORARY"),
                "sha256": current_hash,
                "size": file_size
            })
            total_bytes_to_move += file_size

        except Exception as e:
            blocked_reconciliation.append({
                "file": raw_rel_path,
                "reason": f"READ_EXCEPTION: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })

    recon_path = REGISTRY_OUT / "BLOCKED_AFTER_APPROVAL.json"
    recon_path.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "total_blocked": len(blocked_reconciliation),
        "blocked_items": blocked_reconciliation
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[*] Réconciliation normalisée : {len(verified_items)} exécutables, {len(blocked_reconciliation)} rejetés.")

    if len(verified_items) == 0:
        print("[X] ABORT : Aucun élément valide.")
        sys.exit(1)

    if not execute_mode:
        print("[OK] Dry-Run V7.11.1.2 réussi. Le système est prêt pour --execute.")
        return

    if not check_quarantine_space(total_bytes_to_move):
        print("[X] ABORT: Espace disque insuffisant dans la quarantaine.")
        sys.exit(1)

    print("[*] MUTATION PHYSIQUE AUTORISÉE. Initialisation du Journal Append-Log enrichi...")
    QUARANTINE_ROOT.mkdir(parents=True, exist_ok=True)
    
    tx_log_path = REGISTRY_OUT / "live_transaction_append.logl"
    if tx_log_path.exists(): tx_log_path.unlink()

    committed_transactions = []
    rollback_triggered = False

    try:
        for idx, item in enumerate(verified_items, 1):
            src = item["source_path"]
            rel = item["rel_path"]
            dest = QUARANTINE_ROOT / rel
            dest.parent.mkdir(parents=True, exist_ok=True)

            append_tx_log(tx_log_path, {"step": "START", "file": rel, "timestamp": datetime.now().isoformat()})

            shutil.copy2(src, dest)
            append_tx_log(tx_log_path, {"step": "COPY_OK", "file": rel})

            dest_hash = hashlib.sha256(dest.read_bytes()).hexdigest()
            if dest_hash != item["sha256"]:
                raise RuntimeError(f"ÉCHEC HASH DESTINATION POUR : {rel}")
            append_tx_log(tx_log_path, {"step": "HASH_OK", "file": rel})

            src.unlink()
            if src.exists():
                raise RuntimeError(f"ÉCHEC DE SUPPRESSION SOURCE (FICHIER PERSISTANT) : {rel}")
            
            append_tx_log(tx_log_path, {
                "step": "COMMITTED",
                "file": rel,
                "before_sha256": item["sha256"],
                "after_sha256": dest_hash,
                "size": item["size"],
                "timestamp": datetime.now().isoformat()
            })

            committed_transactions.append({
                "index": idx,
                "source": str(src),
                "destination": str(dest),
                "sha256": item["sha256"]
            })

    except Exception as e:
        print(f"\n[X] ERREUR PENDANT TRANSACTION : {e}")
        print("[*] RESTAURATION PAR ROLLBACK ATOMIQUE...")
        rollback_triggered = True
        
        for tx in reversed(committed_transactions):
            try:
                s_file = Path(tx["source"])
                d_file = Path(tx["destination"])
                if d_file.exists():
                    s_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(d_file, s_file)
                    
                    restored_hash = hashlib.sha256(s_file.read_bytes()).hexdigest()
                    if restored_hash != tx["sha256"]:
                        print(f"[!] ALERTE : Le hash restauré diffère pour {s_file}")
            except Exception as rb_err:
                print(f"[!] Erreur critique rollback : {rb_err}")
        
        print("[*] Rollback terminé et intégrité vérifiée.")
        sys.exit(1)

    if not rollback_triggered:
        print(f"\n[OK] NETTOYAGE V7.11.1.2 COMMITTÉ AVEC SUCCÈS. {len(committed_transactions)} fichiers en quarantaine.")

if __name__ == "__main__":
    run_executor()
