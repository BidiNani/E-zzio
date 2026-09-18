"""
E-ZZIO Core — Exhaustive Baseline Inventory Audit (V7.65.2 Read-Only)
Valide l'intégrité globale du répertoire de baseline : vérifie que tous les fichiers
du manifeste sont conformes et qu'aucun fichier non répertorié (fantôme) n'y subsiste.
"""

import hashlib
import json
import sys
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
BASELINE_DIR = ROOT_DIR / "runtime" / "ecol_baseline_v7.65"
MANIFEST_PATH = BASELINE_DIR / "ecol_baseline_manifest.json"


class ExhaustiveAuditError(Exception):
    """Levée en cas d'anomalie d'inventaire ou de dérive de baseline (Fail-Closed)."""

    pass


def exhaustive_audit():
    print("[*] Lancement de l'audit d'inventaire exhaustif de la baseline V7.65.2...")

    if not BASELINE_DIR.exists():
        raise ExhaustiveAuditError("FAIL CLOSED : Le répertoire de baseline est introuvable.")

    if not MANIFEST_PATH.exists():
        raise ExhaustiveAuditError("FAIL CLOSED : Le manifeste de référence est introuvable.")

    try:
        manifest_data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        raise ExhaustiveAuditError(f"FAIL CLOSED : Erreur de lecture du manifeste : {e}")

    manifest_files = {entry["filename"]: entry for entry in manifest_data.get("files", [])}
    manifest_files["ecol_baseline_manifest.json"] = {"filename": "ecol_baseline_manifest.json", "sha256": "MANAGED"}

    # Recensement de tous les fichiers présents physiquement sur le disque dans le dossier baseline
    actual_files = [p.name for p in BASELINE_DIR.iterdir() if p.is_file()]

    print(f"  * Fichiers répertoriés dans le manifeste : {list(manifest_files.keys())}")
    print(f"  * Fichiers physiques trouvés sur disque  : {actual_files}\n")

    # 1. Vérification des fichiers non répertoriés (Ghost files / Fichiers parasites)
    untracked_files = [f for f in actual_files if f not in manifest_files]
    if untracked_files:
        raise ExhaustiveAuditError(f"FAIL CLOSED CRITIQUE : Fichiers non répertoriés détectés dans la baseline -> {untracked_files}")

    print("  [✓] Aucun fichier parasite ou non répertorié détecté.")

    # 2. Vérification de l'intégrité de chaque fichier inscrit (SHA-256 + Tailles)
    for entry in manifest_data.get("files", []):
        filename = entry["filename"]
        expected_hash = entry["sha256"]
        expected_size = entry["size_bytes"]

        file_path = BASELINE_DIR / filename
        if not file_path.exists():
            raise ExhaustiveAuditError(f"FAIL CLOSED : Fichier requis absent -> {filename}")

        if file_path.stat().st_size != expected_size:
            raise ExhaustiveAuditError(f"FAIL CLOSED : Divergence de taille pour {filename}")

        hasher = hashlib.sha256()
        hasher.update(file_path.read_bytes())
        actual_hash = hasher.hexdigest().lower()

        if actual_hash != expected_hash:
            raise ExhaustiveAuditError(f"FAIL CLOSED : Hash SHA-256 incorrect pour {filename}")

        print(f"  [✓] {filename} : Intégrité cryptographique validée.")

    print("\n" + "=" * 65)
    print(" EXHAUSTIVE BASELINE AUDIT RAPPORT (V7.65.2) : PASS")
    print(" STATUT : RÉPERTOIRE STRICTEMENT CONFORME AU MANIFESTE (ZERO DRIFT)")
    print("=" * 65)


if __name__ == "__main__":
    try:
        exhaustive_audit()
    except Exception as e:
        print(f"\n[!] ALERTE DE SÉCURITÉ : {e}", file=sys.stderr)
        sys.exit(1)
