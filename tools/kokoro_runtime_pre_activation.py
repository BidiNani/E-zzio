"""
Phase 2 : Baseline Avant Activation Runtime de Kokoro-82M.
"""
import hashlib
import json
import subprocess
import time
from pathlib import Path

root = Path("G:/AI/E-zzio")
ext_kokoro = Path("G:/AI/external/capabilities/kokoro-tts")

# 12 Frozen Core Authorities
frozen_authorities = [
    "web_server.py",
    "core/sdk.py",
    "core/cognition/cognitive_gateway.py",
    "core/cognition/model_router.py",
    "core/models/gemini_pool.py",
    "core/providers/gemini_provider.py",
    "core/agent/coding_agent_loop.py",
    "core/capabilities/capability_policy.py",
    "core/capabilities/registry.py",
    "core/memory/unified_gateway.py",
    "core/security/audit_ledger.py",
    "core/security/secrets_vault.py"
]

authorities_hashes = {}
for auth in frozen_authorities:
    p = root / auth
    if p.exists():
        authorities_hashes[auth] = hashlib.sha256(p.read_bytes()).hexdigest()
    else:
        authorities_hashes[auth] = "MISSING"

# Git status
git_st = subprocess.run(["git", "status", "--short"], cwd=root, capture_output=True, text=True).stdout.strip()

# Package versions
import kokoro_onnx
import numpy
import onnxruntime
import soundfile

packages_info = {
    "kokoro_onnx": kokoro_onnx.__version__ if hasattr(kokoro_onnx, "__version__") else "0.6.1",
    "onnxruntime": onnxruntime.__version__,
    "soundfile": soundfile.__version__,
    "numpy": numpy.__version__
}

# Kokoro files hashes
model_p = ext_kokoro / "models" / "kokoro-v0_19.onnx"
voices_p = ext_kokoro / "voices" / "voices.bin"

model_files = {
    "model_path": str(model_p),
    "model_size_bytes": model_p.stat().st_size if model_p.exists() else 0,
    "model_sha256": hashlib.sha256(model_p.read_bytes()).hexdigest() if model_p.exists() else "N/A",
    "voices_path": str(voices_p),
    "voices_size_bytes": voices_p.stat().st_size if voices_p.exists() else 0,
    "voices_sha256": hashlib.sha256(voices_p.read_bytes()).hexdigest() if voices_p.exists() else "N/A"
}

baseline_data = {
    "timestamp": int(time.time()),
    "frozen_core_hashes": authorities_hashes,
    "git_status_short": git_st,
    "packages": packages_info,
    "kokoro_models": model_files,
    "voice_gateway_path": "core/voice/voice_gateway.py",
    "kokoro_adapter_path": "core/capabilities/kokoro_tts_adapter.py",
    "current_status": "PRE_ACTIVATION_BASELINE"
}

out_p = root / "state/audit/optimization/kokoro_runtime_pre_activation_evidence.json"
out_p.parent.mkdir(parents=True, exist_ok=True)
out_p.write_text(json.dumps(baseline_data, indent=2), encoding="utf-8")
print("PRE-ACTIVATION BASELINE SAVED TO:", out_p)
print("FROZEN AUTHORITIES COUNT:", len(authorities_hashes))
