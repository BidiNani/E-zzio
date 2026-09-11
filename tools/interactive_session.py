#!/usr/bin/env python3
"""E-ZZIO — session interactive console (REPL async, clavier).

Boucle : saisie non-bloquante → EzzioMaster.execute_intent → affichage immédiat.
--voice : synthèse Kokoro de la réponse en tâche de fond.
Surveillance missions : alerte dynamique à la terminaison d'un worker.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

POLL_SEC = 3.0


async def voice_play(text: str) -> None:
    """Streaming vocal par phrases : 1re phrase immédiate, suite en fond."""
    import re
    try:
        from core.capabilities.kokoro_tts_adapter import KokoroTTSAdapter
        tts = KokoroTTSAdapter()
        sentences = [s.strip() for s in re.split(r"(?<=[.!?\n])\s+", text[:1200]) if s.strip()]
        if not sentences:
            return
        try:
            import sounddevice as sd
            out = sd.OutputStream(samplerate=24000, channels=1, dtype="float32")
            out.start()
        except Exception:
            out = None
        import io
        for seg in sentences:
            try:
                import soundfile as sf
                r = await asyncio.to_thread(tts.synthesize, seg, "af_bella", 1.0, "fr-fr")
                if r.get("fallback_used") or not r.get("audio_bytes"):
                    continue
                if out is None:
                    continue
                samples, _ = sf.read(io.BytesIO(r["audio_bytes"]), dtype="float32")
                await asyncio.to_thread(out.write, samples.reshape(-1, 1))
            except Exception as exc:
                print(f"[VOIX] segment ignoré : {exc}")
        try:
            if out is not None:
                out.stop()
        except Exception:
            pass
    except Exception as exc:
        print(f"[VOIX] erreur : {exc}")


async def mission_watcher(seen: set[str]) -> None:
    """Alerte les missions workers qui passent à l'état terminal."""
    from core.ezzio_master import ezzio_master
    while True:
        try:
            missions = ezzio_master.registry.list_missions(limit=50)
            for m in missions:
                mid = getattr(m, "mission_id", "?")
                status = getattr(getattr(m, "status", None), "value", "?")
                if status in ("COMPLETED", "FAILED", "CANCELLED") and mid not in seen:
                    seen.add(mid)
                    res = getattr(m, "result", None) or {}
                    summary = res.get("summary", status) if isinstance(res, dict) else status
                    print(f"\n[MISSION NOTIFICATION] #{mid} terminée : {summary}\n"
                          f"Vous > ", end="", flush=True)
        except Exception:
            pass
        await asyncio.sleep(POLL_SEC)


async def repl(use_voice: bool) -> int:
    from core.ezzio_master import ezzio_master
    seen: set[str] = set()
    watch = asyncio.create_task(mission_watcher(seen))
    print("Session E-ZZIO (clavier). 'quit' pour sortir.")
    try:
        while True:
            try:
                prompt = await asyncio.to_thread(input, "\nVous > ")
            except (EOFError, KeyboardInterrupt):
                break
            prompt = (prompt or "").strip()
            if not prompt:
                continue
            if prompt.lower() in ("quit", "exit", "q"):
                break
            try:
                res = await ezzio_master.execute_intent(user_prompt=prompt)
            except Exception as exc:
                print(f"[E-ZZIO] refus/erreur : {exc}")
                continue
            print(f"E-ZZIO > {res.get('response', '')}")
            if use_voice and res.get("response"):
                asyncio.create_task(voice_play(str(res["response"])))
            if res.get("is_async_job"):
                seen.add(str(res.get("mission", "")))
                print(f"(mission #{res.get('mission')} suivie en arrière-plan)")
    finally:
        watch.cancel()
    return 0


def boost_realtime_priority() -> None:
    """Immunité Mode Jeu Win11 : Python + Ollama en ABOVE_NORMAL."""
    try:
        import psutil
        me = psutil.Process()
        try:
            me.nice(psutil.ABOVE_NORMAL_PRIORITY_CLASS)
        except Exception:
            pass
        for proc in psutil.process_iter(["name"]):
            try:
                if (proc.info.get("name") or "").lower() in ("ollama.exe", "ollama"):
                    proc.nice(psutil.ABOVE_NORMAL_PRIORITY_CLASS)
            except Exception:
                continue
        return
    except Exception:
        pass
    try:
        import ctypes
        ABOVE_NORMAL = 0x8000
        ctypes.windll.kernel32.SetPriorityClass(
            ctypes.windll.kernel32.GetCurrentProcess(), ABOVE_NORMAL)
    except Exception as exc:
        print(f"[PRIO] boost impossible : {exc}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Session interactive E-ZZIO")
    ap.add_argument("--no-voice", action="store_true", help="désactive la synthèse vocale")
    args = ap.parse_args()
    from core.system import cpu_tuning
    cpu_tuning.pin_to_ccd1()
    oll = cpu_tuning.pin_ollama_to_ccd1()
    extra = f" Ollama: {oll['pinned'] or 'accès refusé/shell élevé requis'}." if oll["denied"] else ""
    print(f"[CPU-OPT] Processus et Ollama épinglés au CCD1 (Cœurs 6-11, Priorité Haute).{extra}")
    return asyncio.run(repl(not args.no_voice))


if __name__ == "__main__":
    raise SystemExit(main())
