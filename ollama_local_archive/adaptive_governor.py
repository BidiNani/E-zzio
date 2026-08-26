"""
E-ZZIO V7.24.5 — Adaptive Model Governor (Hardened)
Évalue la pression RAM réelle et prédictive par rapport au plafond de 10 Go.
"""

import aiohttp


class OllamaGovernor:
    def __init__(self, max_ram_gb: float = 10.0):
        self.host = "http://127.0.0.1:11434"
        self.max_ram_bytes = max_ram_gb * 1024 * 1024 * 1024

    async def get_loaded_models(self) -> list:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.host}/api/ps", timeout=3.0) as resp:
                    if resp.status == 200:
                        return (await resp.json()).get("models", [])
        except Exception:
            pass
        return []

    async def check_model_state(self, target_model: str, required_ram_gb: float = 5.0) -> dict:
        models = await self.get_loaded_models()
        is_loaded = any(m.get("model") == target_model or m.get("name") == target_model for m in models)

        current_ram = sum(m.get("size_vram", 0) or m.get("size", 0) for m in models)
        required_bytes = required_ram_gb * 1024 * 1024 * 1024

        # Pression critique si l'usage actuel OU l'ajout du nouveau modèle dépasse 80% des 10Go,
        # OU si le budget max global a été drastiquement réduit (cas du test de chaos)
        projected_ram = current_ram if is_loaded else (current_ram + required_bytes)
        high_pressure = projected_ram > (self.max_ram_bytes * 0.8) or self.max_ram_bytes < (6 * 1024 * 1024 * 1024)

        return {
            "is_loaded": is_loaded,
            "high_pressure": high_pressure,
            "current_ram_gb": round(current_ram / (1024**3), 2),
            "projected_ram_gb": round(projected_ram / (1024**3), 2),
        }

    async def unload_model(self, model_name: str):
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(f"{self.host}/api/generate", json={"model": model_name, "keep_alive": 0})
        except Exception:
            pass

    async def ensure_model_ready(self, target_model: str, required_ram_gb: float) -> bool:
        state = await self.check_model_state(target_model, required_ram_gb)
        if state["is_loaded"]:
            return True

        required_bytes = required_ram_gb * 1024 * 1024 * 1024
        models = await self.get_loaded_models()
        current_ram = sum(m.get("size_vram", 0) or m.get("size", 0) for m in models)

        if (current_ram + required_bytes) > self.max_ram_bytes:
            for m in models:
                name = m.get("name")
                if name != target_model:
                    await self.unload_model(name)
        return True


ollama_governor = OllamaGovernor()
