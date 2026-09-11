"""E-ZZIO — tuning système (affinité CPU, priorités)."""
from core.system.cpu_tuning import pin_to_ccd1, pin_ollama_to_ccd1, CCD1_MASK

__all__ = ["pin_to_ccd1", "pin_ollama_to_ccd1", "CCD1_MASK"]
