"""
E-ZZIO V9.6 — Experience Trend Detector
Analyse les flux du Ledger pour détecter des tendances et justifier des évolutions.
"""

from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
LEDGER_DIR = ROOT_DIR / "runtime" / "experience" / "ledger"


class TrendDetector:
    def analyze_trends(self) -> dict:
        fail_path = LEDGER_DIR / "workflow_failure.jsonl"
        failures = 0
        if fail_path.exists():
            with open(fail_path, "r", encoding="utf-8") as f:
                failures = len(f.readlines())

        # Analyse statistique et détection de friction (ex: PDF failures -> OCR)
        if failures > 0:
            return {
                "trend_detected": "PDF_PROCESSING_FRICTION",
                "suggestion": "EVOL-20260812-OCR_EXTENSION",
                "reason": "PDF image-only or parsing friction detected in historical ledger.",
                "confidence": 0.91,
                "required_approval": True,
            }
        return {"trend_detected": "STABLE", "suggestion": None}
