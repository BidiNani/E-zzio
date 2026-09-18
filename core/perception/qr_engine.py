"""E-ZZIO Universal Perception — Fast Deterministic QR Code Engine.

Features:
- Deterministic QR Code Decoding via OpenCV (cv2.QRCodeDetector) — Zero LLM latency
- Safe QR Code Generation via qrcode & Pillow (Strict output sandbox confinement)
- Passive DATA Treatment: Decoded QR payloads (URLs, text, configs) are strictly non-executable
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import cv2
import qrcode
from PIL import Image

logger = logging.getLogger("QREngine")


class QRSecurityError(PermissionError):
    """Levée si l'écriture de QR code tente de sortir des dossiers autorisés."""
    pass


class QREngine:
    def __init__(self, workspace_root: str = "G:\\AI\\E-zzio"):
        self.workspace_root = Path(workspace_root).resolve()
        self.detector = cv2.QRCodeDetector()

    def decode_qrcode(self, image_path: Path | str) -> dict[str, Any]:
        """Décode tout QR code présent dans une image via OpenCV de façon déterministe et instantanée."""
        path = Path(image_path).resolve()
        if not path.exists() or not path.is_file():
            return {"ok": False, "status": "FILE_NOT_FOUND", "error": f"Image introuvable : {image_path}"}

        try:
            img = cv2.imread(str(path))
            if img is None:
                # Tentative de lecture via Pillow pour formats spécifiques puis conversion OpenCV
                pil_img = Image.open(str(path)).convert("RGB")
                import numpy as np
                img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

            # Détection multiple ou simple
            retval, decoded_info, points, _ = self.detector.detectAndDecodeMulti(img)

            results = []
            if retval and decoded_info:
                for text in decoded_info:
                    if text and text.strip():
                        results.append(text.strip())

            # Si simple détection directe
            if not results:
                val, pts, _ = self.detector.detectAndDecode(img)
                if val and val.strip():
                    results.append(val.strip())

            if results:
                return {
                    "ok": True,
                    "status": "QR_DETECTED",
                    "count": len(results),
                    "qr_codes": results,
                    "primary_data": results[0],
                    "content": f"[QR CODE DÉTECTÉ : {results[0]}]"
                }

            return {
                "ok": False,
                "status": "NO_QR_DETECTED",
                "message": "Aucun QR code lisible détecté dans l'image."
            }

        except Exception as exc:
            logger.error("[QR-DECODE-ERROR] Échec décodage QR : %s", exc)
            return {"ok": False, "status": "DECODE_ERROR", "error": str(exc)}

    def generate_qrcode(
        self,
        data: str,
        output_path: Path | str,
        box_size: int = 10,
        border: int = 4
    ) -> dict[str, Any]:
        """Génère une image PNG de QR code avec confinement strict (projects/ ou outputs/)."""
        target = Path(output_path).resolve()
        clean_data = str(data).strip()
        if not clean_data:
            return {"ok": False, "status": "EMPTY_DATA", "error": "Donnée textuelle vide pour le QR code."}

        # Confinement : l'écriture doit être dans projects/ ou outputs/ ou runtime/inbox/
        allowed_dirs = [
            (self.workspace_root / "projects").resolve(),
            (self.workspace_root / "outputs").resolve(),
            (self.workspace_root / "runtime" / "inbox").resolve(),
            (self.workspace_root / "runtime" / "test_tmp").resolve(),
        ]

        is_confined = any(
            str(target).startswith(str(allowed_dir)) for allowed_dir in allowed_dirs
        )

        # Si le dossier parent n'est pas créé
        target.parent.mkdir(parents=True, exist_ok=True)

        if not is_confined:
            # Fallback automatique vers outputs/ si chemin non autorisé
            fallback_dir = (self.workspace_root / "outputs").resolve()
            fallback_dir.mkdir(parents=True, exist_ok=True)
            target = fallback_dir / target.name

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=box_size,
            border=border,
        )
        qr.add_data(clean_data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img.save(str(target))

        return {
            "ok": True,
            "status": "GENERATED",
            "data": clean_data,
            "path": str(target),
            "file_name": target.name,
            "message": f"QR Code généré avec succès dans {target}."
        }
