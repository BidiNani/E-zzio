import requests
import os
import psutil
from pathlib import Path
from typing import Dict, Any

class ModelHealthChecker:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ollama_host = config.get("ollama_host", "http://127.0.0.1:11434")

    def check_ollama(self) -> bool:
        try:
            res = requests.get(f"{self.ollama_host}/api/tags", timeout=2)
            return res.status_code == 200
        except Exception:
            return False

    def check_gemini(self) -> bool:
        return bool(os.getenv("GEMINI_API_KEY"))

    def check_ram_availability(self, required_ram_gb: float) -> bool:
        if required_ram_gb <= 0:
            return True
        free_ram_gb = psutil.virtual_memory().available / (1024 ** 3)
        return free_ram_gb >= required_ram_gb
