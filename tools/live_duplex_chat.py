#!/usr/bin/env python3
"""E-ZZIO — session vocale interactive duplex temps réel (100 % local).

Chaîne : micro sounddevice → VAD VoiceDuplexEngine → faster-whisper STT
→ EzzioMaster.execute_intent → Kokoro ONNX TTS → OutputStream.
Barge-in physique via attach_output_stream() (<50 ms).
"""
from __future__ import annotations

import asyncio
import queue
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SAMPLE_RATE = 16000
CHUNK_MS = 100
STT_MODEL = "tiny"
VOICE = "af_bella"
LANG = "fr-fr"
STOP_WORDS = {"stop", "quit", "quitter", "au revoir", "bonne nuit"}


def main() -> int:
    try:
        import numpy as np
        import sounddevice as sd
    except Exception as exc:
        print(f"[FATAL] audio requis indisponible : {exc}")
        return 2
    try:
        from faster_whisper import WhisperModel
    except Exception as exc:
        print(f"[FATAL] faster-whisper indisponible : {exc}")
        return 2
    from core.capabilities.kokoro_tts_adapter import KokoroTTSAdapter
    from core.ezzio_master import ezzio_master
    from core.voice.voice_duplex_engine import VoiceDuplexEngine

    print("[*] Chargement STT local (tiny, 1er lancement = téléchargement ~75 Mo)...")
    stt = WhisperModel(STT_MODEL, device="cpu", compute_type="int8")
    tts = KokoroTTSAdapter()
    print(f"[*] TTS Kokoro disponible : {tts.is_available}")
    engine = VoiceDuplexEngine()

    mic_q: queue.Queue[bytes] = queue.Queue()

    def mic_cb(indata, frames, time_info, status):
        mic_q.put(bytes(indata))

    mic = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                         blocksize=int(SAMPLE_RATE * CHUNK_MS / 1000),
                         callback=mic_cb)
    out = sd.OutputStream(samplerate=24000, channels=1, dtype="float32")
    mic.start()
    out.start()
    engine.attach_output_stream(out)
    print("[*] Micro + sortie actifs. Parlez (dites « stop » pour quitter).")

    def speak(text: str) -> None:
        segs = [s.strip() for s in text.replace("\n", " ").split(". ") if s.strip()][:6]
        if not segs:
            return
        engine.state = engine.state.SPEAKING
        engine._spoken_text_buffer.clear()
        engine._interrupt_event.clear()
        for seg in segs:
            if engine._interrupt_event.is_set():
                print("[TTS] Coupé par barge-in.")
                break
            r = tts.synthesize(seg, voice=VOICE, lang=LANG)
            raw = r.get("audio_bytes", b"")
            if not raw or r.get("fallback_used"):
                continue
            import io

            import soundfile as sf
            samples, sr = sf.read(io.BytesIO(raw), dtype="float32")
            engine._spoken_text_buffer.append(seg)
            if sr != 24000:
                print(f"[WARN] SR inattendu {sr}, lecture directe.")
            out.write(samples.reshape(-1, 1))
        if not engine._interrupt_event.is_set():
            engine.state = engine.state.IDLE

    buf = bytearray()
    try:
        while True:
            # 1. Accumule ~1,2 s de micro avec VAD continu (barge-in si SPEAKING)
            frames = []
            speech_seen = False
            t_end = time.time() + 1.2
            while time.time() < t_end:
                try:
                    chunk = mic_q.get(timeout=0.1)
                except queue.Empty:
                    continue
                frames.append(chunk)
                if engine.detect_voice_activity(chunk):
                    speech_seen = True
                    if str(engine.state) == "SPEAKING":
                        engine.trigger_barge_in()
                        buf = bytearray()
                        frames = []
                        t_end = time.time() + 1.2
            if not speech_seen:
                continue
            audio = b"".join(frames)
            if len(audio) < SAMPLE_RATE * 2 * 0.4:  # <0,4 s : bruit
                continue
            # 2. STT local
            pcm = np.frombuffer(audio, dtype=np.int16).astype("float32") / 32768.0
            segments, _ = stt.transcribe(pcm, language="fr", beam_size=1)
            text = " ".join(s.text.strip() for s in segments).strip()
            if not text:
                continue
            print(f"[VOUS] {text}")
            if any(w in text.lower() for w in STOP_WORDS):
                speak("Session vocale terminée. À bientôt.")
                break
            # 3. Cerveau (bloquant court, workers en fond si mission)
            res = asyncio.run(ezzio_master.execute_intent(user_prompt=text))
            reply = str(res.get("response", "") or "")[:600]
            if res.get("is_async_job"):
                reply = f"Mission {res.get('mission', '')} lancée en arrière-plan. {reply[:200]}"
            print(f"[E-ZZIO] {reply[:200]}")
            # 4. Sortie vocale (interruptible)
            speak(reply)
    except KeyboardInterrupt:
        print("\n[*] Interruption clavier.")
    finally:
        try:
            mic.stop()
            out.stop()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
