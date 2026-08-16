import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from runtime.test_isolation.v453.async_atomic_writer import AsyncAtomicEventWriter

STORE_DIR = Path("runtime/test_isolation/v453/sandbox_integration_c_async")

def test_v454_async_endurance_load():
    print("[*] Lancement Test C (Async Ryzen Optimized) : 100 000 événements...")
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    store_path = STORE_DIR / "events_endurance_async.jsonl"
    
    # Nettoyage
    for p in STORE_DIR.glob("*"):
        try:
            p.unlink()
        except Exception:
            pass

    writer = AsyncAtomicEventWriter(str(store_path))
    
    total_events = 100_000
    start_time = time.time()
    
    print(f"[*] Enfilement asynchrone de {total_events} événements...")
    for i in range(1, total_events + 1):
        writer.write_event({"seq": i, "payload": f"async_endurance_data_{i}"})
        if i % 25_000 == 0:
            print(f"    -> {i} événements enfilés...")

    print("[*] Vidage de la file d'attente (Flush physique)...")
    writer.close()

    duration = time.time() - start_time
    print(f"[SUCCESS] 100 000 événements traités et commités en {duration:.2f} secondes.")

    # Audit d'intégrité final
    print("[*] Audit d'intégrité final de la charge asynchrone...")
    count = 0
    with open(store_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                data = json.loads(line.strip())
                assert "seq" in data, f"FAIL Test C Async: Clé manquante ligne {line_num}"
                count += 1

    assert count == total_events, f"FAIL Test C Async: Attendu {total_events}, trouvé {count}"
    print(f"[SUCCESS] Intégrité validée : {count} entrées valides, 0 corruption.")

if __name__ == "__main__":
    test_v454_async_endurance_load()
