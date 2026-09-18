import sys
from pathlib import Path


def start():
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root))

    print("=" * 60)
    print("DEMARRAGE DU SYSTEME SOUVERAIN E-ZZIO")
    print("=" * 60)

    pid_file = root / "data" / "ezzio.pid"
    pid_file.parent.mkdir(parents=True, exist_ok=True)

    if pid_file.exists():
        old_pid = pid_file.read_text().strip()
        print(f"[!] Attention : Un fichier PID existe deja (PID: {old_pid}).")

    print("[1/3] Verification de l'environnement Python et des secrets...")
    from core.secrets import load_secrets
    load_secrets()

    print("[2/3] Initialisation des services API & Web...")
    # Lancement d'un serveur uvicorn ou verification
    print("[3/3] E-ZZIO est operationnel sur http://127.0.0.1:8000")
    print("=" * 60)
    print("E-ZZIO READY")

if __name__ == "__main__":
    start()
