"""
Phase 2 : Audit Forensique Préalable de Kokoro-82M.
"""
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

root = Path("G:/AI/E-zzio")
ext_kokoro = Path("G:/AI/external/capabilities/kokoro-tts")

preinstall_data = {
    "audit_timestamp": int(time.time()),
    "target_directory": str(ext_kokoro),
    "python_executable": sys.executable,
    "python_version": sys.version,
    "packages_status": {
        "kokoro": importlib.util.find_spec("kokoro") is not None,
        "kokoro_onnx": importlib.util.find_spec("kokoro_onnx") is not None,
        "onnxruntime": importlib.util.find_spec("onnxruntime") is not None,
        "soundfile": importlib.util.find_spec("soundfile") is not None
    },
    "files_in_external_dir": [],
    "huggingface_cache_kokoro": [],
    "active_ezzio_tts": "ezzio-procedural-tts (core/voice/voice_gateway.py:110-131)",
    "preinstall_classification": "SOURCE_VERIFIED (Catalogue uniquement)"
}

if ext_kokoro.exists():
    for f in ext_kokoro.rglob("*"):
        if f.is_file():
            preinstall_data["files_in_external_dir"].append({
                "path": str(f.relative_to(ext_kokoro)),
                "size_bytes": f.stat().st_size,
                "sha256": hashlib.sha256(f.read_bytes()).hexdigest()
            })

hf_cache = Path("C:/Users/enrik/.cache/huggingface/hub")
if hf_cache.exists():
    for p in hf_cache.glob("*kokoro*"):
        preinstall_data["huggingface_cache_kokoro"].append(str(p))

out_file = root / "state/audit/optimization/kokoro_preinstall_evidence.json"
out_file.parent.mkdir(parents=True, exist_ok=True)
out_file.write_text(json.dumps(preinstall_data, indent=2), encoding="utf-8")
print("PRE-INSTALL AUDIT SAVED TO:", out_file)
print("PRE-INSTALL STATUS:", json.dumps(preinstall_data["packages_status"], indent=2))
