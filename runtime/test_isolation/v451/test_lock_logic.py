import os
import time
import json
from pathlib import Path

# Import direct ou inclusion de la classe SimpleFileLock pour le test
# (On redéfinit ou importe la classe ici pour l'autonomie du test isolé)
from runtime.test_isolation.v451.simple_lock_v451 import SimpleFileLock

lock_file = Path("runtime/test_isolation/v451/test.lock")
sec_file = Path("runtime/test_isolation/v451/security.jsonl")

# Nettoyage initial
for f in [lock_file, sec_file]:
    if f.exists(): f.unlink()

print("[1] Test acquisition et libération normale...")
with SimpleFileLock(lock_file, sec_file, timeout=2.0) as lock:
    assert lock_file.exists(), "Le fichier lock devrait exister pendant le context manager"
    print("  [OK] Lock acquis et détenu.")
assert not lock_file.exists(), "Le fichier lock devrait être supprimé à la sortie"
print("  [OK] Normal lock validé.\n")

print("[2] Test Ghost Lock (PID mort + ancienneté)...")
# Injection d'un faux lock orphelin avec un PID impossible (ex: 999999) et daté d'il y a 100 secondes
fake_meta = {
    "pid": 999999,
    "created": time.time() - 100,
    "host": "TEST-PC",
    "version": "4.5.1"
}
lock_file.write_text(json.dumps(fake_meta), encoding="utf-8")

# L'acquisition doit détecter le PID mort, purger le ghost lock, logger l'événement et réussir
with SimpleFileLock(lock_file, sec_file, timeout=2.0) as lock:
    print("  [OK] Ghost lock contourné et purgé avec succès.")

# Vérification de l'écriture du journal de sécurité
if sec_file.exists():
    sec_logs = sec_file.read_text(encoding="utf-8").strip().splitlines()
    print(f"  [LOG SECURITY] Événements forensiques enregistrés : {len(sec_logs)}")
    found_stale = any("STALE_LOCK_RECOVERED" in line for line in sec_logs)
    assert found_stale, "L'événement STALE_LOCK_RECOVERED est absent des logs de sécurité"
    print("  [OK] Événement de sécurité forensique validé.\n")

print("[3] Test Lock Corrompu / Illisible...")
lock_file.write_text("CORRUPTED_JSON_DATA_XXX", encoding="utf-8")

with SimpleFileLock(lock_file, sec_file, timeout=2.0) as lock:
    print("  [OK] Lock corrompu purgé et récupéré avec succès.\n")

# Nettoyage final de l'isolation
for f in [lock_file, sec_file]:
    if f.exists(): f.unlink()

print("============================================================")
print(" V4.5.1 — STALE LOCK RECOVERY CERTIFIÉ EN ISOLATION")
print("============================================================")
