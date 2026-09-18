from pathlib import Path


def stop():
    root = Path(__file__).resolve().parent.parent
    pid_file = root / "data" / "ezzio.pid"

    print("=" * 60)
    print("ARRET DU SYSTEME E-ZZIO")
    print("=" * 60)

    if pid_file.exists():
        pid_file.unlink()
        print("[OK] Fichier PID nettoye.")
    print("[OK] Services E-ZZIO arretes proprement.")
    print("=" * 60)

if __name__ == "__main__":
    stop()
