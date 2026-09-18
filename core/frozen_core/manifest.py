"""Frozen Core manifest — calcul et vérification d'intégrité.

Le manifest est stocké dans docs/FROZEN_CORE_MANIFEST.json.
Il est la SEULE source de vérité pour les hashes des fichiers protégés.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

# Racine du repo (remonte depuis core/frozen_core/manifest.py)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MANIFEST_PATH = REPO_ROOT / "docs" / "FROZEN_CORE_MANIFEST.json"

# Liste canonique des fichiers sous Frozen Core.
# Ajouter/retirer un fichier = modifier cette liste + regénérer le manifest.
FROZEN_FILES: tuple[str, ...] = (
    "core/capabilities/capability_policy.py",
    "core/capabilities/registry.py",
    "core/security/audit_ledger.py",
)


class ManifestDriftError(RuntimeError):
    """Levée quand un fichier Frozen Core diffère de son hash attendu."""

    def __init__(self, drifts: dict[str, dict[str, str]]) -> None:
        self.drifts = drifts
        lines = ["Frozen Core drift detected:"]
        for path, info in drifts.items():
            lines.append(f"  {path}")
            lines.append(f"    attendu : {info['expected']}")
            lines.append(f"    réel    : {info['actual']}")
        super().__init__("\n".join(lines))


def compute_hash(filepath: Path) -> str:
    """Hash SHA256 normalisé : contenu lu en binaire, hex uppercase.

    On ne normalise PAS les fins de ligne (on veut détecter tout changement).
    """
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def load_manifest() -> dict[str, Any]:
    """Charge le manifest. Supporte les formats 'components' et 'files'."""
    if not MANIFEST_PATH.exists():
        return {"version": 1, "components": {}}
    raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    # Normalisation interne : toujours exposer 'components' avec {sha256: ...}
    if "components" in raw:
        return raw
    if "files" in raw:
        # Migrer l'ancien format vers le nouveau
        return {
            "version": raw.get("version", 1),
            "components": {
                path: {"sha256": h}
                for path, h in raw["files"].items()
            },
        }
    return {"version": 1, "components": {}}


def _get_manifest_hashes(manifest: dict[str, Any]) -> dict[str, str]:
    """Extrait {path: sha256} du manifest, peu importe le format."""
    if "components" in manifest:
        return {path: meta["sha256"] for path, meta in manifest["components"].items()}
    if "files" in manifest:
        return dict(manifest["files"])
    return {}


def save_manifest(manifest: dict[str, Any]) -> None:
    """Écrit le manifest au format 'components' (compatible tests existants)."""
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False)
    MANIFEST_PATH.write_text(payload + "\n", encoding="utf-8", newline="\n")


def regenerate_manifest() -> dict[str, Any]:
    """Recalcule tous les hashes et réécrit le manifest au format 'components'."""
    components: dict[str, dict[str, str]] = {}
    for rel in FROZEN_FILES:
        fp = REPO_ROOT / rel
        if not fp.exists():
            raise FileNotFoundError(f"Frozen Core file introuvable : {rel}")
        components[rel] = {"sha256": compute_hash(fp)}
    manifest = {"version": 1, "components": components}
    save_manifest(manifest)
    return manifest


def verify_integrity() -> None:
    """Vérifie l'intégrité. Lève ManifestDriftError si dérive détectée.

    Utilisé par tous les tests Frozen Core (gate unique).
    """
    manifest = load_manifest()
    expected_files: dict[str, str] = _get_manifest_hashes(manifest)
    drifts: dict[str, dict[str, str]] = {}

    # 1. Fichiers protégés absents du manifest
    for rel in FROZEN_FILES:
        if rel not in expected_files:
            drifts[rel] = {"expected": "<absent du manifest>", "actual": "<non vérifié>"}
            continue

        fp = REPO_ROOT / rel
        if not fp.exists():
            drifts[rel] = {"expected": expected_files[rel], "actual": "<fichier manquant>"}
            continue

        actual = compute_hash(fp)
        if actual != expected_files[rel]:
            drifts[rel] = {"expected": expected_files[rel], "actual": actual}

    # 2. Entrées du manifest qui ne sont plus dans FROZEN_FILES
    for rel in expected_files:
        if rel not in FROZEN_FILES:
            drifts[rel] = {
                "expected": expected_files[rel],
                "actual": "<plus dans FROZEN_FILES>",
            }

    if drifts:
        raise ManifestDriftError(drifts)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "regen":
        m = regenerate_manifest()
        print(f"Manifest regénéré : {len(m['files'])} hashes")
    else:
        try:
            verify_integrity()
            print("Frozen Core : OK")
        except ManifestDriftError as e:
            print(str(e))
            sys.exit(1)
