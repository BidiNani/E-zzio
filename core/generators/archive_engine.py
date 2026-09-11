"""
E-ZZIO Sovereign Generator — Archive Engine (ZIP & TAR).
Compression et extraction sécurisées avec protection Anti-Zip Slip intégrale.
"""
from __future__ import annotations
import os
import zipfile
import tarfile
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("ArchiveEngine")


class ArchiveSecurityError(PermissionError):
    """Levée en cas de tentative d'extraction hors du répertoire cible (Anti-Zip Slip)."""
    pass


class ArchiveEngine:
    """Moteur souverain de manipulation d'archives compressées sécurisées."""

    def __init__(self, workspace_root: str = "G:\\AI\\E-zzio"):
        self.workspace_root = Path(workspace_root).resolve()
        self.exports_dir = self.workspace_root / "runtime" / "exports"
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    def create_zip(
        self,
        archive_name: str,
        source_paths: List[str],
        base_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Crée une archive ZIP à partir d'une liste de fichiers ou dossiers.
        """
        clean_name = os.path.basename(archive_name.strip())
        if not clean_name.endswith(".zip"):
            clean_name += ".zip"

        out_path = self.exports_dir / clean_name
        base_path = Path(base_dir).resolve() if base_dir else self.workspace_root

        added_files = []
        with zipfile.ZipFile(str(out_path), 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            for s_path_str in source_paths:
                p = Path(s_path_str)
                if not p.is_absolute():
                    p = (base_path / p).resolve()

                if not p.exists():
                    logger.warning("[ARCHIVE] Chemin source introuvable ignoré : %s", p)
                    continue

                if p.is_file():
                    arcname = p.relative_to(base_path) if p.is_relative_to(base_path) else p.name
                    zf.write(str(p), str(arcname))
                    added_files.append(str(arcname))
                elif p.is_dir():
                    for root, _, files in os.walk(p):
                        for f in files:
                            full_f = Path(root) / f
                            arcname = full_f.relative_to(base_path) if full_f.is_relative_to(base_path) else full_f.name
                            zf.write(str(full_f), str(arcname))
                            added_files.append(str(arcname))

        logger.info("[ARCHIVE] Archive ZIP créée : %s (%d fichiers)", out_path, len(added_files))

        return {
            "ok": True,
            "filename": clean_name,
            "path": str(out_path),
            "size_bytes": out_path.stat().st_size,
            "total_files": len(added_files)
        }

    def safe_extract_zip(
        self,
        archive_path: str,
        destination_dir: str
    ) -> Dict[str, Any]:
        """
        Extrait un fichier ZIP en garantissant une immunité absolue contre le Zip Slip (traversal).
        """
        arc_p = Path(archive_path).resolve()
        if not arc_p.exists():
            raise FileNotFoundError(f"Archive introuvable : {archive_path}")

        dest_p = Path(destination_dir).resolve()
        dest_p.mkdir(parents=True, exist_ok=True)

        extracted_files = []
        with zipfile.ZipFile(str(arc_p), 'r') as zf:
            for member in zf.infolist():
                # Calcul de la destination résolue
                target_path = (dest_p / member.filename).resolve()

                # Vérification Anti-Zip Slip
                try:
                    if os.path.commonpath([str(dest_p), str(target_path)]) != str(dest_p):
                        raise ArchiveSecurityError(
                            f"[FAIL-CLOSED] Tentative d'évasion Anti-Zip Slip détectée sur {member.filename}"
                        )
                except ValueError:
                    raise ArchiveSecurityError(f"[FAIL-CLOSED] Chemin malveillant : {member.filename}")

                zf.extract(member, str(dest_p))
                extracted_files.append(str(target_path.relative_to(dest_p)))

        logger.info("[ARCHIVE] Extraction sécurisée réussie : %d fichiers dans %s", len(extracted_files), dest_p)

        return {
            "ok": True,
            "extracted_count": len(extracted_files),
            "destination": str(dest_p),
            "files": extracted_files
        }
