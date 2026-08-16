import sys
import json
import time
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from runtime.memory.atomic_writer import AtomicEventWriter

STORE_DIR = Path("runtime/test_isolation/v453/sandbox_integration_b")

def test_v454_active_flux_kill():
    print("[*] Lancement Test B : Coupure brutale (Kill) pendant un flux actif...")
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    store_path = STORE_DIR / "events_kill.jsonl"
    
    # Nettoyage
    for p in STORE_DIR.glob("*"):
        try:
            p.unlink()
        except Exception:
            pass

    worker_script = Path(__file__).parent / "worker_flood.py"

    # Démarrage du sous-processus worker
    proc = subprocess.Popen([sys.executable, str(worker_script), str(store_path)])
    
    # Laisse tourner un court instant pour alimenter le flux
    time.sleep(0.5)
    
    # Coupure brutale (Kill -9 / Stop-Process -Force)
    print(f"[CHAOS] Arrêt forcé du processus d'écriture (PID: {proc.pid})...")
    proc.kill()
    proc.wait()

    # Instanciation de récupération (Boot recovery post-crash)
    print("[*] Instanciation du recovery post-coupure active...")
    recovery_writer = AtomicEventWriter(str(store_path))
    
    # Écriture d'un événement post-recovery pour valider la reprise du service
    recovery_writer.write_event({"seq": 9999, "status": "post_recovery_ok"})

    # Audit d'intégrité final du store
    assert store_path.exists(), "FAIL Test B: Le store principal a disparu"
    
    lines = []
    with open(store_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                lines.append(json.loads(line.strip()))

    assert len(lines) > 0, "FAIL Test B: Le store est vide après coupure"
    
    print(f"[OK] Store récupéré avec succès. Nombre d'entrées valides : {len(lines)}")
    print("[SUCCESS] Test B V4.5.4 validé : Coupure en plein flux gérée sans corruption.")

if __name__ == "__main__":
    test_v454_active_flux_kill()
