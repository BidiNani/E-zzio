from typing import List, Dict, Any
from .schemas import ModelRequest

class ModelSelector:
    def __init__(self, catalog: Dict[str, Any]):
        self.catalog = catalog

    def select_cascade(self, req: ModelRequest) -> List[str]:
        cascade = []

        if req.budget == "offline_only":
            if req.task == "code":
                cascade.extend(["qwen2.5-coder:7b", "qwen3:8b", "Qwen3-Coder-30B-A3B"])
            elif req.task == "vision":
                cascade.extend(["gemma4e4b:latest"])
            else:
                cascade.extend(["qwen3:8b", "qwen2.5-coder:7b"])
            return cascade

        # Règle local_first / cloud_first
        if req.complexity in ["high", "critical"] and req.budget != "offline_only":
            cascade.extend(["gemini-2.5-pro", "gemini-3.6-flash"])
            if req.task == "code":
                cascade.append("qwen2.5-coder:7b")
            else:
                cascade.append("qwen3:8b")
        else:
            if req.task == "code":
                cascade.extend(["qwen2.5-coder:7b", "gemini-3.6-flash", "qwen3:8b"])
            elif req.task == "vision":
                cascade.extend(["gemma4e4b:latest", "gemini-3.6-flash"])
            else:
                cascade.extend(["qwen3:8b", "gemini-3.6-flash"])

        # Dédoublonnage en conservant l'ordre
        seen = set()
        ordered_cascade = []
        for model in cascade:
            if model in self.catalog and model not in seen:
                seen.add(model)
                ordered_cascade.append(model)

        return ordered_cascade
