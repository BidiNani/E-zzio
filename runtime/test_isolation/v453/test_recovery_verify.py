import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from runtime.memory.atomic_writer import AtomicEventWriter

def verify_recovery():
    store_file = Path("runtime/test_isolation/v453/sandbox_data/events_crash.jsonl")
    
    # Réinstanciation du writer -> déclenche _recover_interrupted_swap()
    writer = AtomicEventWriter(str(store_file))
    
    assert store_file.exists() == True, "FAIL: Le store n'a pas été restauré"
    
    with open(store_file, "r", encoding="utf-8") as f:
        content = f.read()
        assert "initial" in content or "pending_crash" in content
        
    print("[SUCCESS] Auto-recovery V4.5.3 certifié : Le store est dans un état valide après crash.")

if __name__ == "__main__":
    verify_recovery()
