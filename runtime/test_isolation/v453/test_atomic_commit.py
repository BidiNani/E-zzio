import os
from atomic_writer import AtomicEventWriter
from pathlib import Path

def test_full_atomic_lifecycle():
    store_dir = Path("runtime/test_isolation/v453/sandbox_data")
    store_dir.mkdir(parents=True, exist_ok=True)
    store_file = store_dir / "events.jsonl"
    
    # Nettoyage sandbox
    for p in store_dir.glob("*"):
        p.unlink()

    writer = AtomicEventWriter(str(store_file))
    
    # Écriture 1 : Premier événement (création store)
    assert writer.write_event({"id": 1, "payload": "alpha"}) == True
    assert store_file.exists() == True
    
    with open(store_file, "r", encoding="utf-8") as f:
        assert "alpha" in f.read()

    # Écriture 2 : Second événement (déclenche le backup .bak)
    assert writer.write_event({"id": 2, "payload": "beta"}) == True
    assert writer.bak_path.exists() == True
    
    with open(writer.bak_path, "r", encoding="utf-8") as f:
        assert "alpha" in f.read()

    with open(store_file, "r", encoding="utf-8") as f:
        assert "beta" in f.read()

    print("[SUCCESS] Tests C & D validés : Cycle complet et double buffering opérationnels.")

if __name__ == "__main__":
    test_full_atomic_lifecycle()
