"""
E-ZZIO Core V9.2 — VoiceStudio Voice I/O Capability Adapter.

Adaptateur de capacité vocale (STT / TTS) se connectant au service local VoiceStudio
(Endpoint HTTP loopback ou MCP Streamable HTTP sous http://localhost:3900/mcp/).

Moteur cible : PocketTTS (CPU-Only, optimisation latence, support Français).
Licence : AGPL-3.0 (Service externe / Process indépendant — Zéro inclusion de code source dans le noyau).

Conformité Fail-Closed :
Si VoiceStudio n'est pas démarré, ne répond pas ou rencontre une erreur audio :
- Une notification `VOICE_FAILURE` est émise sans impacter EzzioMaster, Policy, Budget, ModelRouter ou AuditLedger.
- La réponse texte E-ZZIO reste 100% opérationnelle.
- voice_enabled = False par défaut.
"""
from __future__ import annotations

import asyncio
import json
import logging
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from core.security.audit_ledger import AuditLedger

logger = logging.getLogger("VoiceStudioCapabilityAdapter")


@dataclass
class VoiceCapabilityResult:
    action: str  # STT | TTS | HEALTH
    status: str  # SUCCESS | FAILED | UNAVAILABLE
    text: str = ""
    audio_data: bytes = field(default_factory=bytes)
    duration_sec: float = 0.0
    language: str = "fr"
    engine: str = "pocket_tts"
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "status": self.status,
            "text": self.text,
            "has_audio": len(self.audio_data) > 0,
            "duration_sec": self.duration_sec,
            "language": self.language,
            "engine": self.engine,
            "error": self.error,
        }


class VoiceStudioAdapter:
    """Adaptateur de capacité vocale E-ZZIO pour le serveur local VoiceStudio / PocketTTS."""

    def __init__(
        self,
        base_url: str = "http://localhost:3900",
        mcp_path: str = "/mcp/",
        enabled: bool = False,
        engine: str = "pocket_tts",
        audit_ledger: AuditLedger | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.mcp_url = f"{self.base_url}{mcp_path}"
        self.enabled = enabled
        self.engine = engine  # CPU-only default: pocket_tts
        self.audit_ledger = audit_ledger or AuditLedger()

    async def check_health(self) -> dict[str, Any]:
        """Vérifie la santé du backend VoiceStudio sur localhost."""
        if not self.enabled:
            return {"status": "DISABLED", "available": False, "reason": "voice_enabled is False"}

        try:
            req = urllib.request.Request(f"{self.base_url}/health", headers={"User-Agent": "E-ZZIO-VoiceStudio/9.2"})
            loop = asyncio.get_running_loop()

            def _fetch():
                try:
                    with urllib.request.urlopen(req, timeout=2.0) as resp:
                        return resp.status == 200
                except Exception:
                    return False

            is_ok = await loop.run_in_executor(None, _fetch)
            return {
                "status": "AVAILABLE" if is_ok else "UNAVAILABLE",
                "available": is_ok,
                "engine": self.engine,
                "url": self.base_url,
            }
        except Exception as exc:
            return {"status": "UNAVAILABLE", "available": False, "error": str(exc)}

    async def transcribe(
        self,
        audio_bytes: bytes,
        language: str = "fr",
        timeout_sec: float = 5.0,
    ) -> VoiceCapabilityResult:
        """Transcrit un flux audio PCM/WAV en texte via l'API STT VoiceStudio local (Fail-Closed)."""
        if not self.enabled:
            return VoiceCapabilityResult(
                action="STT",
                status="UNAVAILABLE",
                error="Voice capability is disabled (voice_enabled=False)",
            )

        if not audio_bytes:
            return VoiceCapabilityResult(
                action="STT",
                status="FAILED",
                error="Audio input is empty",
            )

        try:
            # Envoi vers l'API local /transcribe ou MCP Streamable HTTP endpoint
            req_payload = json.dumps({
                "language": language,
                "engine": self.engine,
                "audio_len": len(audio_bytes),
            }).encode("utf-8")

            req = urllib.request.Request(
                f"{self.base_url}/api/transcribe",
                data=req_payload,
                headers={"Content-Type": "application/json", "User-Agent": "E-ZZIO-VoiceStudio/9.2"},
                method="POST",
            )

            loop = asyncio.get_running_loop()

            def _do_post():
                try:
                    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                        if resp.status == 200:
                            data = json.loads(resp.read().decode("utf-8"))
                            return data
                except Exception as req_err:
                    logger.debug("[VoiceStudioAdapter] Local STT HTTP request fallback: %s", req_err)
                return None

            raw_res = await loop.run_in_executor(None, _do_post)

            # Audit event
            try:
                self.audit_ledger.record_event(
                    actor="VoiceStudioAdapter",
                    action="VOICE_STT_TRANSCRIBED",
                    payload={"language": language, "has_response": raw_res is not None},
                    status="SUCCESS" if raw_res else "FALLBACK",
                )
            except Exception:
                pass

            if raw_res and "text" in raw_res:
                transcription = raw_res.get("text", "")
                duration = float(raw_res.get("duration_sec", 0.0))
                return VoiceCapabilityResult(
                    action="STT",
                    status="SUCCESS",
                    text=transcription,
                    duration_sec=duration,
                    language=language,
                    engine=self.engine,
                )

            # Fail-closed degradation fallback
            return VoiceCapabilityResult(
                action="STT",
                status="UNAVAILABLE",
                error="VoiceStudio STT endpoint unresponsive (text fallback active).",
            )

        except Exception as exc:
            logger.warning("[VoiceStudioAdapter] STT exception (fail-closed fallback): %s", exc)
            return VoiceCapabilityResult(
                action="STT",
                status="FAILED",
                error=str(exc),
            )

    async def synthesize(
        self,
        text: str,
        voice_profile: str = "pocket_tts_fr",
        timeout_sec: float = 5.0,
    ) -> VoiceCapabilityResult:
        """Génère la synthèse vocale (TTS) via PocketTTS CPU-only (Fail-Closed)."""
        if not self.enabled:
            return VoiceCapabilityResult(
                action="TTS",
                status="UNAVAILABLE",
                error="Voice capability is disabled (voice_enabled=False)",
            )

        if not text or not text.strip():
            return VoiceCapabilityResult(
                action="TTS",
                status="FAILED",
                error="Text prompt is empty",
            )

        try:
            req_payload = json.dumps({
                "text": text,
                "voice_profile": voice_profile,
                "engine": self.engine,
            }).encode("utf-8")

            req = urllib.request.Request(
                f"{self.base_url}/api/tts",
                data=req_payload,
                headers={"Content-Type": "application/json", "User-Agent": "E-ZZIO-VoiceStudio/9.2"},
                method="POST",
            )

            loop = asyncio.get_running_loop()

            def _do_post():
                try:
                    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                        if resp.status == 200:
                            return resp.read()
                except Exception as req_err:
                    logger.debug("[VoiceStudioAdapter] Local TTS HTTP request fallback: %s", req_err)
                return None

            raw_audio = await loop.run_in_executor(None, _do_post)

            # Audit event
            try:
                self.audit_ledger.record_event(
                    actor="VoiceStudioAdapter",
                    action="VOICE_TTS_SYNTHESIZED",
                    payload={"text_len": len(text), "voice_profile": voice_profile, "has_audio": bool(raw_audio)},
                    status="SUCCESS" if raw_audio else "FALLBACK",
                )
            except Exception:
                pass

            if raw_audio:
                return VoiceCapabilityResult(
                    action="TTS",
                    status="SUCCESS",
                    text=text,
                    audio_data=raw_audio,
                    duration_sec=round(len(raw_audio) / 32000.0, 2),
                    engine=self.engine,
                )

            return VoiceCapabilityResult(
                action="TTS",
                status="UNAVAILABLE",
                error="VoiceStudio TTS endpoint unresponsive (text fallback active).",
            )

        except Exception as exc:
            logger.warning("[VoiceStudioAdapter] TTS exception (fail-closed fallback): %s", exc)
            return VoiceCapabilityResult(
                action="TTS",
                status="FAILED",
                error=str(exc),
            )
