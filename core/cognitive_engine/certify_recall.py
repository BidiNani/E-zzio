import sys
from pathlib import Path
ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path: sys.path.insert(0, str(ROOT_DIR))
from core.cognitive_engine.cognitive_gatekeeper import CognitiveGatekeeper

def run_certification():
    gk = CognitiveGatekeeper()
    test_vectors = [
        {"name": "Test 1 — Identité", "path": Path("registry/core/constitution.md"), "content": "Core identity laws", "expected_type": "identity_core", "expected_index": True},
        {"name": "Test 2 — RPG réel", "path": Path("registry/game/druid_build.md"), "content": "wotlk feral druid raid macro talents", "expected_type": "RPG_MEMORY", "expected_index": True},
        {"name": "Test 3 — Faux RPG", "path": Path("runtime/audit/backup_report.txt"), "content": "backup raid completed", "expected_type": "QUARANTINE", "expected_index": False},
        {"name": "Test 4 — Sandbox", "path": Path("runtime/test_isolation/v460/sandbox_stress/events.jsonl"), "content": "fuzz test", "expected_type": "SYNTHETIC_NOISE", "expected_index": False},
        {"name": "Test 5 — Inconnu", "path": Path("random/new/file.json"), "content": "data", "expected_type": "QUARANTINE", "expected_index": False}
    ]

    print("\n[V7.59.3.1] CERTIFICATION LANCEE...")
    for t in test_vectors:
        res = gk.evaluate(t["path"], t["content"])
        if res["memory_type"] == t["expected_type"] and res["indexable"] == t["expected_index"]:
            print(f"[PASS] {t['name']}")
        else:
            print(f"[FAIL] {t['name']} -> Attendu: {t['expected_type']}/{t['expected_index']}, Obtenu: {res['memory_type']}/{res['indexable']}")

run_certification()
