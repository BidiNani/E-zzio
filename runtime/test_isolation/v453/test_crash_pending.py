import os
from atomic_writer import AtomicEventWriter
from pathlib import Path

def test_pending_isolation():
    store = Path("events.jsonl")
    writer = AtomicEventWriter(str(store))
    
    # Simulation: Write triggered, but crash before replace
    writer.write_event({"test": "data"})
    
    # Assertions
    assert store.exists() == False, "FAIL: Store ne devrait pas exister (crash)"
    assert writer.pending_path.exists() == True, "FAIL: Pending devrait persister"
    print("[OK] Test A: Crash pendant pending validé.")

if __name__ == "__main__":
    test_pending_isolation()
