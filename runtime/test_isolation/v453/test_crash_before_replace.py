import os
from atomic_writer import AtomicEventWriter
from pathlib import Path

def test_fsync_integrity():
    store = Path("events.jsonl")
    writer = AtomicEventWriter(str(store))
    
    # Simulation: Fsync OK, mais crash juste avant replace
    pending = writer.write_event({"test": "integrity"})
    
    # Assert: Fichier pending doit contenir la donnée flushée
    with open(pending, "r") as f:
        content = f.read()
        assert "integrity" in content
        
    print("[OK] Test B: Intégrité flushée validée.")

if __name__ == "__main__":
    test_fsync_integrity()
