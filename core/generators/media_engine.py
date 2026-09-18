"""
E-ZZIO Sovereign Generator — Media & 3D Engine.
Génération locale de maillages 3D (GLTF/OBJ), synthèses audio WAV et wrappers FFmpeg.
"""
from __future__ import annotations

import logging
import math
import os
import struct
import wave
from pathlib import Path
from typing import Any

logger = logging.getLogger("MediaEngine")


class MediaEngine:
    """Moteur souverain de génération multimédia (Audio, 3D, Vidéo)."""

    def __init__(self, workspace_root: str = "G:\\AI\\E-zzio"):
        self.workspace_root = Path(workspace_root).resolve()
        self.exports_dir = self.workspace_root / "runtime" / "exports"
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    def generate_tone_wav(
        self,
        filename: str,
        frequency_hz: float = 440.0,
        duration_sec: float = 1.0,
        sample_rate: int = 44100
    ) -> dict[str, Any]:
        """
        Génère une onde sonore pure WAV (STT/TTS testing ou alertes sonores).
        """
        clean_name = os.path.basename(filename.strip())
        if not clean_name.endswith(".wav"):
            clean_name += ".wav"

        out_path = self.exports_dir / clean_name
        num_samples = int(sample_rate * duration_sec)

        with wave.open(str(out_path), 'w') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)

            for i in range(num_samples):
                t = float(i) / sample_rate
                # Atténuation douce en fin de son
                envelope = 1.0 - (i / num_samples) * 0.2
                sample_val = int(32767.0 * 0.5 * envelope * math.sin(2.0 * math.pi * frequency_hz * t))
                wav_file.writeframes(struct.pack('<h', sample_val))

        logger.info("[MEDIA-ENGINE] Fichier WAV généré : %s", out_path)
        return {
            "ok": True,
            "filename": clean_name,
            "path": str(out_path),
            "duration_sec": duration_sec,
            "size_bytes": out_path.stat().st_size
        }

    def generate_3d_cube_obj(
        self,
        filename: str,
        size: float = 1.0,
        color_name: str = "CyberBlue"
    ) -> dict[str, Any]:
        """
        Génère un maillage 3D Wavefront (.obj) standard valide pour Godot, Blender ou WebGL.
        """
        clean_name = os.path.basename(filename.strip())
        if not clean_name.endswith(".obj"):
            clean_name += ".obj"

        out_path = self.exports_dir / clean_name
        s = size / 2.0

        # Sommets d'un cube
        vertices = [
            (-s, -s, -s), (s, -s, -s), (s, s, -s), (-s, s, -s),
            (-s, -s, s), (s, -s, s), (s, s, s), (-s, s, s)
        ]

        # Faces (triangulées)
        faces = [
            (1, 2, 3), (1, 3, 4),  # Back
            (5, 6, 7), (5, 7, 8),  # Front
            (1, 5, 8), (1, 8, 4),  # Left
            (2, 6, 7), (2, 7, 3),  # Right
            (4, 3, 7), (4, 7, 8),  # Top
            (1, 2, 6), (1, 6, 5)   # Bottom
        ]

        lines = [
            f"# E-ZZIO Autonomous 3D Generator — {color_name}",
            f"o Cube_{color_name}"
        ]
        for v in vertices:
            lines.append(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}")

        for f in faces:
            lines.append(f"f {f[0]} {f[1]} {f[2]}")

        out_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("[MEDIA-ENGINE] Objet 3D OBJ généré : %s", out_path)

        return {
            "ok": True,
            "filename": clean_name,
            "path": str(out_path),
            "vertices_count": len(vertices),
            "faces_count": len(faces),
            "size_bytes": out_path.stat().st_size
        }
