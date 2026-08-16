import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from segmented_manager import SegmentManager

def test_segment_lifecycle():
    print("[*] Test du cycle de vie des segments et du manifeste...")
    sandbox = Path("runtime/test_isolation/v456/store")
    
    # Nettoyage sandbox
    for p in sandbox.glob("**/*"):
        if p.is_file():
            p.unlink()

    # Instanciation avec une petite taille max pour forcer la rotation rapidement (ex: 1 Ko)
    manager = SegmentManager(str(sandbox), max_segment_size=1024)
    
    active_path = manager.get_active_segment_path()
    assert active_path.name == "segment_000001.jsonl"

    # Écriture de données pour saturer le segment 1
    data_chunk = json.dumps({"payload": "A" * 500}) + "\n"
    
    with open(active_path, "a", encoding="utf-8") as f:
        f.write(data_chunk)
        f.write(data_chunk) # Dépasse 1024 octets

    assert manager.check_rotation_needed(10) == True
    manager.rotate_segment()

    # Vérification post-rotation
    new_active = manager.get_active_segment_path()
    assert new_active.name == "segment_000002.jsonl"
    assert len(manager.manifest["segments"]) == 1
    assert manager.manifest["segments"][0]["id"] == 1
    assert manager.manifest["segments"][0]["sha256"] != ""

    print("[SUCCESS] Test de segmentation et rotation validé avec succès.")

if __name__ == "__main__":
    test_segment_lifecycle()
