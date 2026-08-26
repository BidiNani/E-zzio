import json
from pathlib import Path

config_path = Path(r"G:\AI\E-zzio\runtime\model_router\config.json")
if config_path.exists():
    cfg = json.loads(config_path.read_text(encoding="utf-8"))

    if "catalog" not in cfg:
        cfg["catalog"] = {}
    cfg["catalog"]["gemma2:2b"] = {
        "provider": "ollama",
        "capabilities": ["chat", "general", "fast_reply"],
        "max_complexity": "low",
        "options": {"num_predict": 512, "temperature": 0.7},
    }

    if "routes" not in cfg:
        cfg["routes"] = {}
    cfg["routes"]["general"] = "gemma2:2b"
    cfg["routes"]["chat"] = "gemma2:2b"
    cfg["default_model"] = "gemma2:2b"

    config_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    print("[OK] config.json : gemma2:2b est le nouveau modèle par défaut.")
