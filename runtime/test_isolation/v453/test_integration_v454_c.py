import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from runtime.memory.atomic_writer import AtomicEventWriter

STORE_DIR = Path("runtime/test_isolation/v453/sandbox_integration_c")

def test_v454_endurance_load():
    print("[*] Lancement Test C : Charge prolongée (100 000 événements)...")
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    store_path = STORE_DIR / "events_endurance.jsonl"
    
    # Nettoyage
    for p in STORE_DIR.glob("*"):
        try:
            p.unlink()
        except Exception:
            pass

    writer = AtomicEventWriter(str(store_path))
    
    total_events = 100_000
    start_time = time.time()
    
    print(f"[*] Début de l'écriture intensive de {total_events} événements...")
    for i in range(1, total_events + 1):
        writer.write_event({"seq": i, "payload": f"endurance_data_{i}"})
        if i % 25_000 == 0:
            print(f"    -> {i} événements écrits...")

    duration = time.time() - start_time
    print(f"[OK] Écriture de {total_events} événements terminée en {duration:.2f} secondes.")

    # Audit d'intégrité final complet
    print("[*] Audit d'intégrité final de la charge 100k...")
    count = 0
    with open(store_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                data = json.loads(line.strip())
                assert "seq" in data, f"FAIL Test C: Clé manquante ligne {line_num}"
                count += 1

    assert count == total_events, f"FAIL Test C: Nombre d'événements attendu {total_events}, trouvé {count}"
    print(f"[SUCCESS] Test C V4.5.4 validé : 100 000 événements validés, 0 corruption, intégrité totale.")

if __name__ == "__main__":
    test_v454_endurance_load()
