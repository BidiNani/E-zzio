"""
E-ZZIO : Téléchargement et Vérification de Qwen3.5-9B-MTP.
"""
import hashlib
import json
from pathlib import Path

from huggingface_hub import hf_hub_download

root = Path("G:/AI/E-zzio")
ext_models = Path("G:/AI/external/models")

target_dir = ext_models / "qwen3.5-9b-mtp"
target_dir.mkdir(parents=True, exist_ok=True)
filename = "Qwen3.5-9B-Q4_K_M.gguf"
target_file = target_dir / filename

print(f"=== DOWNLOADING qwen3.5-9b-mtp : {filename} ===")
if not target_file.exists() or target_file.stat().st_size == 0:
    hf_hub_download(
        repo_id="unsloth/Qwen3.5-9B-MTP-GGUF",
        filename=filename,
        local_dir=str(target_dir),
        local_dir_use_symlinks=False
    )

sha256 = hashlib.sha256()
with open(target_file, "rb") as f:
    while chunk := f.read(1024 * 1024 * 16):
        sha256.update(chunk)
file_hash = sha256.hexdigest()
file_size = target_file.stat().st_size

print(f"DONE: qwen3.5-9b-mtp -> {file_size} bytes | SHA256: {file_hash}")

# Update installation evidence JSON
ev_p = root / "state/audit/optimization/model_installation_evidence.json"
data = json.loads(ev_p.read_text(encoding="utf-8")) if ev_p.exists() else {}
data["qwen3.5-9b-mtp"] = {
    "tool_id": "qwen3.5-9b-mtp",
    "repo_id": "unsloth/Qwen3.5-9B-MTP-GGUF",
    "filename": filename,
    "local_path": str(target_file),
    "size_bytes": file_size,
    "size_gb": round(file_size / (1024**3), 2),
    "sha256": file_hash,
    "parameters": "9.7B",
    "quantization": "Q4_K_M",
    "license_code": "Apache-2.0",
    "license_weights": "Qwen Research / Open Weight",
    "install_status": "INSTALLED (Physical GGUF in external sandbox)"
}
ev_p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
print("UPDATED INSTALLATION EVIDENCE AT:", ev_p)
