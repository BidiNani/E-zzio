import sys
import json
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from segmented_recovery import SegmentedRecoveryEngine

SANDBOX = Path("runtime/test_isolation/v456/sandbox_chaos")

def setup_sandbox():
    if SANDBOX.exists():
        for p in SANDBOX.glob("**/*"):
            try:
                p.unlink()
            except Exception:
                pass
    SANDBOX.mkdir(parents=True, exist_ok=True)

def test_a_crash_mid_write():
    print("\n--- TEST A : Crash pendant écriture active (EOF tronqué structuré) ---")
    setup_sandbox()
    
    seg_dir = SANDBOX / "segments"
    seg_dir.mkdir(parents=True, exist_ok=True)
    active_seg = seg_dir / "segment_000001.jsonl"
    
    # Simulation d'un write standard JSONL avec \n et crash sur la dernière ligne
    content = json.dumps({"event": 1}) + "\n" + json.dumps({"event": 2}) + "\n" + '{"event": incom'
    active_seg.write_text(content, encoding="utf-8")
    
    # Lancement du recovery
    engine = SegmentedRecoveryEngine(str(SANDBOX))
    
    # Vérification : exact 2 lignes valides préservées
    lines = active_seg.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2, f"FAIL Test A: Attendu 2 lignes valides, trouvé {len(lines)}"
    assert json.loads(lines[0])["event"] == 1
    assert json.loads(lines[1])["event"] == 2
    print("[SUCCESS] Test A validé : EOF tronqué purgé proprement, 100% des données valides conservées.")

def test_b_corrupted_manifest():
    print("\n--- TEST B : Manifeste complètement corrompu ---")
    setup_sandbox()
    
    seg_dir = SANDBOX / "segments"
    seg_dir.mkdir(parents=True, exist_ok=True)
    
    (seg_dir / "segment_000001.jsonl").write_text(json.dumps({"data": "alpha"}) + "\n", encoding="utf-8")
    (seg_dir / "segment_000002.jsonl").write_text(json.dumps({"data": "beta"}) + "\n", encoding="utf-8")
    
    manifest_path = SANDBOX / "manifest.json"
    manifest_path.write_text('{"active_segment_id": 999, "corrupted', encoding="utf-8")
    
    engine = SegmentedRecoveryEngine(str(SANDBOX))
    
    assert engine.manifest["active_segment_id"] == 2, f"FAIL Test B: ID actif attendu 2, trouvé {engine.manifest['active_segment_id']}"
    assert len(engine.manifest["segments"]) == 1, "FAIL Test B: Le segment 1 doit être dans les fermés"
    assert engine.manifest["segments"][0]["id"] == 1
    print("[SUCCESS] Test B validé : Manifeste corrompu détecté, reconstruit avec succès.")

if __name__ == "__main__":
    test_a_crash_mid_write()
    test_b_corrupted_manifest()
    print("\n=============================================================")
    print(" STATUT : V4.5.6.2 BYTE-LEVEL RECOVERY CHAOS DRILL VALIDÉ")
    print("=============================================================")
