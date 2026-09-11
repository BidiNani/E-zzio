"""
E-ZZIO : Téléchargement, Hachage et Enregistrement des Modèles Candidats Externes.
"""
import os
import sys
import json
import time
import hashlib
from pathlib import Path
from huggingface_hub import hf_hub_download

root = Path("G:/AI/E-zzio")
ext_models = Path("G:/AI/external/models")
ext_models.mkdir(parents=True, exist_ok=True)

candidates = [
    {
        "tool_id": "ministral-3-3b-instruct",
        "repo_id": "unsloth/Ministral-3-3B-Instruct-2512-GGUF",
        "filename": "Ministral-3-3B-Instruct-2512-Q4_K_M.gguf",
        "license_code": "Apache-2.0",
        "license_weights": "Mistral Non-Commercial / Research or Open Weight",
        "param": "3.8B",
        "quant": "Q4_K_M"
    },
    {
        "tool_id": "gemma-4-e4b-it",
        "repo_id": "unsloth/gemma-4-E4B-it-GGUF",
        "filename": "gemma-4-E4B-it-Q4_K_M.gguf",
        "license_code": "Apache-2.0",
        "license_weights": "Gemma Open Terms",
        "param": "4.3B",
        "quant": "Q4_K_M"
    }
]

download_records = {}

for c in candidates:
    target_dir = ext_models / c["tool_id"]
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / c["filename"]
    
    print(f"=== DOWNLOADING {c['tool_id']} : {c['filename']} ===")
    t0 = time.perf_counter()
    if not target_file.exists() or target_file.stat().st_size == 0:
        downloaded_path = hf_hub_download(
            repo_id=c["repo_id"],
            filename=c["filename"],
            local_dir=str(target_dir),
            local_dir_use_symlinks=False
        )
    lat_s = time.perf_counter() - t0
    
    # Calculate SHA256 in chunks
    sha256 = hashlib.sha256()
    with open(target_file, "rb") as f:
        while chunk := f.read(1024 * 1024 * 16):
            sha256.update(chunk)
    file_hash = sha256.hexdigest()
    file_size = target_file.stat().st_size
    
    download_records[c["tool_id"]] = {
        "tool_id": c["tool_id"],
        "repo_id": c["repo_id"],
        "filename": c["filename"],
        "local_path": str(target_file),
        "size_bytes": file_size,
        "size_gb": round(file_size / (1024**3), 2),
        "sha256": file_hash,
        "parameters": c["param"],
        "quantization": c["quant"],
        "license_code": c["license_code"],
        "license_weights": c["license_weights"],
        "install_status": "INSTALLED (Physical GGUF in external sandbox)"
    }
    print(f"DONE: {c['tool_id']} -> {file_size} bytes | SHA256: {file_hash}")

out_p = root / "state/audit/optimization/model_installation_evidence.json"
out_p.parent.mkdir(parents=True, exist_ok=True)
out_p.write_text(json.dumps(download_records, indent=2, ensure_ascii=False), encoding="utf-8")
print("INSTALLATION EVIDENCE SAVED TO:", out_p)
