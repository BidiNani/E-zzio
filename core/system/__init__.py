"""E-ZZIO — tuning système (affinité CPU, priorités)."""
from core.system.cpu_tuning import CCD1_MASK, pin_ollama_to_ccd1, pin_to_ccd1

__all__ = ["pin_to_ccd1", "pin_ollama_to_ccd1", "CCD1_MASK"]
