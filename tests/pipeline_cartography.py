import inspect
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path("G:/AI/E-zzio")
sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 72)
print(" E-ZZIO — NOMINAL PIPELINE FORENSIC CARTOGRAPHY (READ-ONLY)")
print("=" * 72)

# 1. Analyse de la distribution des états dans le registre persistant
registry_path = PROJECT_ROOT / "data" / "models" / "registry.json"
if registry_path.exists():
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
        models = data.get("models", {})
        distribution = {}
        for k, v in models.items():
            state = v.get("lifecycle", "UNKNOWN")
            distribution[state] = distribution.get(state, 0) + 1
        print(f"\n[REGISTRY STATE DISTRIBUTION] Total entrées : {len(models)}")
        for state, count in sorted(distribution.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {state} : {count} modèle(s)")
    except Exception as exc:
        print(f"\n[REGISTRY STATE DISTRIBUTION ERROR] {exc}")
else:
    print(f"\n[REGISTRY STATE DISTRIBUTION] Fichier introuvable : {registry_path}")

# 2. Inspection de ModelLifecycleManager (Matrice des transitions et acteurs)
try:
    from core.models.lifecycle import ModelLifecycleManager
    print("\n--- [LIFECYCLE MANAGER CARTOGRAPHY] ---")
    sig = inspect.signature(ModelLifecycleManager.transition) if hasattr(ModelLifecycleManager, "transition") else "N/A"
    print(f"  transition signature : {sig}")

    # Recherche des matrices de transition ou règles d'acteurs dans le source
    source_lc = inspect.getsource(ModelLifecycleManager)
    print("  Extrait des règles de transition (ModelLifecycleManager) :")
    for line in source_lc.splitlines():
        if "actor" in line.lower() or "state" in line.lower() or "transition" in line.lower() or "allowed" in line.lower():
            print(f"    {line.strip()}")
except Exception as exc:
    print(f"\n[LIFECYCLE CARTOGRAPHY ERROR] {exc}")

# 3. Inspection de QualificationGate
try:
    from core.models.qualification.gate import QualificationGate
    print("\n--- [QUALIFICATION GATE CARTOGRAPHY] ---")
    source_gate = inspect.getsource(QualificationGate)
    print("  Extrait de QualificationGate :")
    for line in source_gate.splitlines():
        if "def " in line or "return " in line or "score" in line.lower() or "qualif" in line.lower():
            print(f"    {line.strip()}")
except Exception as exc:
    print(f"\n[QUALIFICATION CARTOGRAPHY ERROR] {exc}")

# 4. Inspection de AutonomousModelFabric (Découverte et orchestration)
try:
    from core.models.fabric import AutonomousModelFabric
    print("\n--- [FABRIC DISCOVERY & ORCHESTRATION CARTOGRAPHY] ---")
    methods = [m[0] for m in inspect.getmembers(AutonomousModelFabric, predicate=inspect.function) if not m[0].startswith("_")]
    print(f"  Méthodes publiques de la Fabric : {methods}")

    source_fab = inspect.getsource(AutonomousModelFabric)
    print("  Extrait de AutonomousModelFabric (découverte / transition) :")
    for line in source_fab.splitlines():
        if "discover" in line.lower() or "transition" in line.lower() or "active" in line.lower():
            print(f"    {line.strip()}")
except Exception as exc:
    print(f"\n[FABRIC CARTOGRAPHY ERROR] {exc}")

print("\n" + "=" * 72)
print(" CARTOGRAPHIE TERMINÉE — AUCUNE MODIFICATION EFFECTUÉE")
print("=" * 72)
