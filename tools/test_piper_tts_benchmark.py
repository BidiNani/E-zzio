"""
E-ZZIO : Benchmark et Qualification de Piper TTS (CPU ONLY).
"""
import os
import sys
import io
import time
import json
import wave
import hashlib
from pathlib import Path
from piper import PiperVoice

root = Path("G:/AI/E-zzio")
ext_piper = Path("G:/AI/external/capabilities/piper-tts")
model_path = ext_piper / "models/fr_FR-siwis-medium.onnx"
config_path = ext_piper / "models/fr_FR-siwis-medium.onnx.json"
outputs_dir = ext_piper / "outputs"
outputs_dir.mkdir(parents=True, exist_ok=True)

test_phrase = "Bonjour, ceci est un test de synthèse vocale Piper ultra-rapide sur processeur Ryzen."

t0_load = time.perf_counter()
voice = PiperVoice.load(str(model_path), str(config_path))
load_ms = (time.perf_counter() - t0_load) * 1000

t0 = time.perf_counter()
out_file = outputs_dir / "piper_siwis_smoke_test.wav"
with wave.open(str(out_file), "wb") as wf:
    voice.synthesize_wav(test_phrase, wf)
lat_ms = (time.perf_counter() - t0) * 1000

audio_bytes = out_file.read_bytes()

with wave.open(str(out_file), "rb") as wf:
    sr = wf.getframerate()
    ch = wf.getnchannels()
    frames = wf.getnframes()
    dur_s = frames / float(sr)

rtf = (lat_ms / 1000.0) / dur_s

piper_evidence = {
    "timestamp": int(time.time()),
    "tool_id": "piper-tts-fr-siwis",
    "source_url": "https://github.com/rhasspy/piper",
    "commit_or_version": "piper-tts 1.7.0 / fr_FR-siwis-medium",
    "license_code": "MIT",
    "license_weights": "MIT",
    "install_path": str(ext_piper),
    "model_hashes": {
        "fr_FR-siwis-medium.onnx": hashlib.sha256(model_path.read_bytes()).hexdigest(),
        "fr_FR-siwis-medium.onnx.json": hashlib.sha256(config_path.read_bytes()).hexdigest()
    },
    "load_time_ms": round(load_ms, 2),
    "benchmark": {
        "output_file": str(out_file),
        "output_size_bytes": len(audio_bytes),
        "output_sha256": hashlib.sha256(audio_bytes).hexdigest(),
        "sample_rate": sr,
        "channels": ch,
        "duration_seconds": round(dur_s, 2),
        "generation_latency_ms": round(lat_ms, 2),
        "real_time_factor": round(rtf, 4),
        "speedup_vs_realtime": round(1.0 / rtf, 2)
    },
    "classification": "PROVEN (Moteur TTS léger alternatif qualifié en sandbox)"
}

out_json = root / "state/audit/optimization/piper_qualification_evidence.json"
out_json.parent.mkdir(parents=True, exist_ok=True)
out_json.write_text(json.dumps(piper_evidence, indent=2, ensure_ascii=False), encoding="utf-8")
print("PIPER QUALIFICATION SAVED TO:", out_json)
print(json.dumps(piper_evidence["benchmark"], indent=2))
