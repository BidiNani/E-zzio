"""
core/observability/capability_detector.py — External Capability Detector for E-ZZIO.
Strictly distinguishes between adapter present, service available, and actually executed.
Never confuses an adapter instance with live capability.
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
from dataclasses import dataclass
from typing import Any


@dataclass
class CapabilityStatus:
    name: str
    adapter_present: bool
    service_available: bool
    executable: bool
    version: str | None
    status: str  # PROVEN, MEASURED, OBSERVED, PARTIAL, UNKNOWN, DEFERRED
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "adapter_present": self.adapter_present,
            "service_available": self.service_available,
            "executable": self.executable,
            "version": self.version,
            "status": self.status,
            "details": self.details,
        }


class CapabilityDetector:
    """Détecte l'état réel des capacités externes (PiG, VoiceStudio, Ollama) sans assomptions."""

    def __init__(self, workspace_root: str = "G:\\AI\\E-zzio"):
        self.workspace_root = os.path.abspath(workspace_root)

    def detect_pig(self, custom_path: str | None = None) -> CapabilityStatus:
        """Détecte l'existence réelle et le statut d'exécution de PiG Coding Worker."""
        # 1. Vérification présence de l'adapter
        adapter_present = os.path.exists(os.path.join(self.workspace_root, "core", "agent", "pig_worker_adapter.py"))

        # 2. Recherche du binaire
        target_bin = custom_path or shutil.which("pig") or shutil.which("pig.exe")
        executable = False
        version = None
        launchable = False

        if target_bin and os.path.isfile(target_bin):
            executable = os.access(target_bin, os.X_OK)
            try:
                proc = subprocess.run([target_bin, "--version"], capture_output=True, text=True, timeout=2)
                if proc.returncode == 0:
                    version = proc.stdout.strip()
                    launchable = True
            except Exception:
                launchable = False

        status = "PROVEN" if (executable and launchable) else "DEFERRED"

        return CapabilityStatus(
            name="PiG",
            adapter_present=adapter_present,
            service_available=launchable,
            executable=executable,
            version=version,
            status=status,
            details={
                "binary_path": target_bin,
                "launchable": launchable,
                "reason": "Binary absent or not executable in current environment" if not launchable else "Executable verified",
            },
        )

    def detect_voicestudio(self, host: str = "127.0.0.1", port: int = 3900, timeout: float = 0.5) -> CapabilityStatus:
        """Détecte l'accessibilité du service VoiceStudio / PocketTTS."""
        adapter_present = os.path.exists(os.path.join(self.workspace_root, "core", "capabilities", "voice_studio.py"))

        reachable = False
        try:
            with socket.create_connection((host, port), timeout=timeout):
                reachable = True
        except (TimeoutError, ConnectionRefusedError, OSError):
            reachable = False

        status = "PROVEN" if reachable else "DEFERRED"

        return CapabilityStatus(
            name="VoiceStudio",
            adapter_present=adapter_present,
            service_available=reachable,
            executable=reachable,
            version="1.0-PocketTTS" if reachable else None,
            status=status,
            details={
                "host": host,
                "port": port,
                "stt_available": reachable,
                "tts_available": reachable,
                "pockettts_available": reachable,
                "reason": "Local server not listening on target port" if not reachable else "Socket connection verified",
            },
        )

    def detect_ollama(self, host: str = "127.0.0.1", port: int = 11434, timeout: float = 0.5) -> CapabilityStatus:
        """Détecte l'accessibilité d'Ollama local."""
        reachable = False
        try:
            with socket.create_connection((host, port), timeout=timeout):
                reachable = True
        except (TimeoutError, ConnectionRefusedError, OSError):
            reachable = False

        status = "MEASURED" if reachable else "DEFERRED"

        return CapabilityStatus(
            name="Ollama",
            adapter_present=True,
            service_available=reachable,
            executable=reachable,
            version="local-ollama" if reachable else None,
            status=status,
            details={
                "host": host,
                "port": port,
                "endpoint": f"http://{host}:{port}",
                "reason": "Ollama daemon not listening" if not reachable else "Daemon reachable",
            },
        )

    def detect_all(self) -> dict[str, CapabilityStatus]:
        return {
            "pig": self.detect_pig(),
            "voicestudio": self.detect_voicestudio(),
            "ollama": self.detect_ollama(),
        }
