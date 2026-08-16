import json
from pathlib import Path

ROOT = Path(r"G:\AI\E-zzio")
config_file = ROOT / "runtime" / "model_router" / "config.json"

if config_file.exists():
    config = json.loads(config_file.read_text(encoding="utf-8"))
    
    # 1. Ajustement du catalogue : Définition des rôles
    if "catalog" in config:
        # Modèle rapide pour chat / general
        config["catalog"]["gemma4e4b"] = {
            "provider": "ollama",
            "capabilities": ["chat", "general", "fast_reply"],
            "max_complexity": "low",
            "keep_alive": "30m",
            "options": {
                "num_ctx": 4096,
                "num_predict": 200,
                "temperature": 0.7
            }
        }
        
        # Qwen3 restreint au raisonnement / code complexe
        if "qwen3:8b" in config["catalog"]:
            config["catalog"]["qwen3:8b"]["capabilities"] = ["reasoning", "code"]
            config["catalog"]["qwen3:8b"]["options"] = {
                "num_ctx": 4096,
                "num_predict": 1024,
                "temperature": 0.3,
                "think": False  # Désactivation du thinking superflu par défaut
            }

    # 2. Ajustement des routes par défaut
    if "routes" in config:
        config["routes"]["general"] = "gemma4e4b"
        config["routes"]["chat"] = "gemma4e4b"
        config["routes"]["reasoning"] = "qwen3:8b"
        config["routes"]["code"] = "qwen3:8b"

    config_file.write_text(json.dumps(config, indent=2), encoding="utf-8")
    print("[OK] Model Router mis à jour : gemma4e4b priorisé pour le chat, qwen3:8b réservé au raisonnement.")
else:
    print("[FAIL] config.json introuvable.")
