"""
E-ZZIO : Inventaire Initial Forensique des Modèles Locaux (Avant Découverte).
"""
import hashlib
import json
from pathlib import Path

import psutil

root = Path("G:/AI/E-zzio")
ext_dir = Path("G:/AI/external")

# 1. Check Frozen Core Integrity
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

base_p = root / "state/audit/optimization/kokoro_runtime_pre_activation_evidence.json"
base_data = json.loads(base_p.read_text(encoding="utf-8"))
base_hashes = base_data["frozen_core_hashes"]

drift = 0
for auth in frozen_authorities:
    curr_h = hashlib.sha256((root / auth).read_bytes()).hexdigest()
    if curr_h != base_hashes.get(auth):
        drift += 1

# 2. Initial Physical Inventory
inv = {
    "timestamp": 1788048380,
    "frozen_core_drift": drift,
    "hardware": {
        "cpu": "AMD Ryzen 9 5900X (12C / 24T)",
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_threads": psutil.cpu_count(logical=True),
        "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 1),
        "gpu_usage": 0,
        "cuda": "OFF"
    },
    "external_directories": {
        "models_dir": str(ext_dir / "models"),
        "capabilities_dir": str(ext_dir / "capabilities"),
        "llama_cpp_dir": str(ext_dir / "llama.cpp")
    },
    "ollama_models_present": [
        {"model": "ez-router:latest", "parent": "phi4-mini:latest", "param": "3.8B", "quant": "Q4_K_M", "size_gb": 2.49},
        {"model": "ez-core-safe:latest", "parent": "qwen3.5:9b", "param": "9.7B", "quant": "Q4_K_M", "size_gb": 6.59},
        {"model": "ez-agent-hermes:latest", "parent": "hermes3:8b", "param": "8.0B", "quant": "Q4_0", "size_gb": 4.66},
        {"model": "ez-core-free:latest", "parent": "llama3.1-8b-abliterated", "param": "8.0B", "quant": "Q5_K_M", "size_gb": 5.73},
        {"model": "ez-rag-expert:latest", "parent": "ornith-1.5:9b", "param": "9.0B", "quant": "Q4_K_M", "size_gb": 6.55},
        {"model": "bge-m3:latest", "parent": "bge-m3", "param": "566.7M", "quant": "F16", "size_gb": 1.15},
        {"model": "nomic-embed-text:latest", "parent": "nomic-embed-text", "param": "137M", "quant": "F16", "size_gb": 0.27}
    ],
    "target_candidates_status_before": {
        "qwen3.5_9b_mtp": "NOT_INSTALLED",
        "ministral_3": "NOT_INSTALLED",
        "gemma_4_e4b": "NOT_INSTALLED",
        "piper_tts": "INSTALLED"
    }
}

out_p = root / "state/audit/optimization/model_inventory_before.json"
out_p.parent.mkdir(parents=True, exist_ok=True)
out_p.write_text(json.dumps(inv, indent=2, ensure_ascii=False), encoding="utf-8")
print("INVENTORY BEFORE SAVED TO:", out_p)
print(f"FROZEN CORE DRIFT: {drift}")
