import sys
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from runtime.experience.analytics.trend_detector import TrendDetector
from runtime.autonomy.policy_engine import ActionPolicyEngine

# Analyse des tendances dans le Ledger
detector = TrendDetector()
trend = detector.analyze_trends()

# Evaluation par la politique d'autonomie
engine = ActionPolicyEngine()
policy_eval = engine.evaluate_action("ADD_CAPABILITY", confidence=trend.get("confidence", 0.0))

print("\n" + "=" * 60)
print(" 🏛️ E-ZZIO ANALYTICS ENGINE — FRICTION TRIGGER TEST")
print("=" * 60)
print(f" Friction Détectée        : {trend['trend_detected']}")
print(f" Motif / Cause            : {trend['reason']}")
print(f" Proposition d'Évolution  : {trend['suggestion']}")
print(f" Score de Confiance       : {trend['confidence']}")
print(f" Requis Validation Humaine: {trend['required_approval']}")
print("-" * 60)
print(f" Décision d'Autonomie     : [{policy_eval['action']}] -> {policy_eval['reason']}")
print(f" Niveau de Gouvernance    : {policy_eval['autonomy_level']}")
print("-" * 60)
print(" 🟢 RESULTAT : PROPOSITION GENEREE & ROUTEE VERS VALIDATION")
print("=" * 60 + "\n")
