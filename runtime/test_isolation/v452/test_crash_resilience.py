from pathlib import Path
import json
from store_v452 import MemoryEventStoreV452

store_file = Path("test_events.jsonl")
quarantine_file = Path("test_quarantine.jsonl")

def cleanup():
    for f in [store_file, quarantine_file]:
        if f.exists(): f.unlink()

print("--- [CAS A & D] Test Crash Terminal (JSON tronqué en fin de fichier) ---")
cleanup()
store = MemoryEventStoreV452(path=str(store_file), quarantine_path=str(quarantine_file))
store.append("SYSTEM_EVENT", {"seq": 1})
store.append("SYSTEM_EVENT", {"seq": 2})
store.append("SYSTEM_EVENT", {"seq": 3})
initial_size = store_file.stat().st_size

with store_file.open("a", encoding="utf-8") as f:
    f.write('{"schema":"4.5.2","payload":{"ski')

corrupted_size = store_file.stat().st_size
assert corrupted_size > initial_size

store_recovered = MemoryEventStoreV452(path=str(store_file), quarantine_path=str(quarantine_file))
print(f"  -> Statut d'intégrité après récup : {store_recovered.integrity_status}")
print(f"  -> Événements validés : {store_recovered.checked_events_count}")

assert store_recovered.integrity_status == "VALID"
assert store_recovered.checked_events_count == 3

final_size = store_file.stat().st_size
assert final_size == initial_size

assert quarantine_file.exists()
q_lines = quarantine_file.read_text(encoding="utf-8").strip().splitlines()
assert len(q_lines) == 1
q_event = json.loads(q_lines[0])
assert q_event["type"] == "CRASH_WRITE_RECOVERED"
assert q_event["details"]["reason"] == "TRUNCATED_JSON_AT_EOF"
print("  [OK] Cas A & D validés : Crash terminal récupéré, taille tronquée, quarantaine OK.\n")

print("--- [CAS B] Test Corruption Historique (Ligne intermédiaire modifiée) ---")
cleanup()
store = MemoryEventStoreV452(path=str(store_file), quarantine_path=str(quarantine_file))
store.append("SYSTEM_EVENT", {"seq": 1})
store.append("SYSTEM_EVENT", {"seq": 2})
store.append("SYSTEM_EVENT", {"seq": 3})

lines = store_file.read_text(encoding="utf-8").splitlines()
ev_mid = json.loads(lines[0])
ev_mid["payload"]["seq"] = 999
lines[0] = json.dumps(ev_mid, ensure_ascii=False)
store_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

store_hist_fail = MemoryEventStoreV452(path=str(store_file), quarantine_path=str(quarantine_file))
print(f"  -> Statut sur corruption historique : {store_hist_fail.integrity_status}")
print(f"  -> Erreur associée : {store_hist_fail.integrity_error}")

assert store_hist_fail.integrity_status == "FAILED"
assert "HISTORICAL_CHAIN_COMPROMISE" in store_hist_fail.integrity_error
print("  [OK] Cas B validé : Corruption historique strictement bloquée.")

cleanup()
print("\n============================================================")
print(" V4.5.2 — CRASH WRITE RESILIENCE CERTIFIÉ EN ISOLATION")
print("============================================================\n")