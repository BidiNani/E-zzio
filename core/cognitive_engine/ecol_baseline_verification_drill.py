"""
E-ZZIO Core — Baseline Verification Drill (V7.65.1 Read-Only)
Vérifie l'intégrité cryptographique absolue de la baseline ECOL V7.65
en comparant les hashes réels au manifeste de référence. Aucune écriture.
"""

import hashlib
import json
import sys
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
BASELINE_DIR = ROOT_DIR / "runtime" / "ecol_baseline_v7.65"
MANIFEST_PATH = BASELINE_DIR / "ecol_baseline_manifest.json"


class BaselineIntegrityError(Exception):
    """Levée en cas de divergence ou de falsification de la baseline certifiée (Fail-Closed)."""

    pass


def verify_baseline():
    print("[*] Lancement du Baseline Verification Drill V7.65.1 (Mode Lecture Seule)...")

    if not BASELINE_DIR.exists():
        raise BaselineIntegrityError("FAIL CLOSED CRITIQUE : Le répertoire de baseline V7.65 est introuvable.")

    if not MANIFEST_PATH.exists():
        raise BaselineIntegrityError("FAIL CLOSED CRITIQUE : Le manifeste de baseline est introuvable.")

    # Chargement du manifeste de référence
    try:
        manifest_data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        raise BaselineIntegrityError(f"FAIL CLOSED : Corruption du manifeste de baseline : {e}")

    print(f"  * Baseline Version : {manifest_data.get('baseline_version')}")
    print(f"  * Horodatage UTC   : {manifest_data.get('sealing_timestamp_utc')}")
    print(f"  * Périmètre        : {manifest_data.get('governance_scope')}\n")

    verified_count = 0
    for entry in manifest_data.get("files", []):
        filename = entry["filename"]
        expected_hash = entry["sha256"]
        expected_size = entry["size_bytes"]

        file_path = BASELINE_DIR / filename
        if not file_path.exists():
            raise BaselineIntegrityError(f"FAIL CLOSED : Fichier de baseline manquant -> {filename}")

        # Vérification de la taille
        actual_size = file_path.stat().st_size
        if actual_size != expected_size:
            raise BaselineIntegrityError(
                f"FAIL CLOSED : Divergence de taille pour {filename} (Attendu: {expected_size}, Trouvé: {actual_size})"
            )

        # Calcul du SHA-256 actuel
        hasher = hashlib.sha256()
        hasher.update(file_path.read_bytes())
        actual_hash = hasher.hexdigest().lower()

        if actual_hash != expected_hash:
            raise BaselineIntegrityError(
                f"FAIL CLOSED CRITIQUE : Altération détectée sur {filename} !\n  Attendu : {expected_hash}\n  Trouvé  : {actual_hash}"
            )

        print(f"  [✓] {filename} : SHA-256 VERIFIÉ IDENTIQUE")
        verified_count += 1

    print("\n" + "=" * 65)
    print(f" BASELINE VERIFICATION RAPPORT (V7.65.1) : SUCCESS ({verified_count} artéfacts)")
    print(" STATUT : INTÉGRITÉ ABSOLUE CONFIRMÉE (ZERO DRIFT)")
    print("=" * 65)


if __name__ == "__main__":
    try:
        verify_baseline()
    except Exception as e:
        print(f"\n[!] ALERTE DE SÉCURITÉ : {e}", file=sys.stderr)
        sys.exit(1)
