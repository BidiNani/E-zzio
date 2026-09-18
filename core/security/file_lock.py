"""
E-ZZIO V7.28.3 — Native Kernel-Level File Lock
Utilise les primitives de verrouillage du système d'exploitation (msvcrt / fcntl)
pour garantir une exclusion mutuelle multi-processus indestructible et auto-libérée par l'OS en cas de crash.
"""

import os
import random
import sys
import time
from pathlib import Path


class ProcessFileLock:
    def __init__(self, lock_file_path: Path, timeout: float = 30.0):
        self.lock_path = Path(lock_file_path)
        self.timeout = timeout
        self.fd = None

    def __enter__(self):
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        # Ouverture ou création du fichier de verrou dédié
        self.fd = os.open(str(self.lock_path), os.O_CREAT | os.O_RDWR)
        start_time = time.time()
        attempt = 0

        while True:
            try:
                if sys.platform == "win32":
                    import msvcrt

                    # S'assure que le fichier possède au moins 1 octet pour le verrouillage par segment Windows
                    os.lseek(self.fd, 0, os.SEEK_END)
                    if os.lseek(self.fd, 0, os.SEEK_CUR) == 0:
                        os.write(self.fd, b"X")
                    os.lseek(self.fd, 0, os.SEEK_SET)
                    # Verrouillage exclusif non-bloquant de 1 octet au début du fichier
                    msvcrt.locking(self.fd, msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError:
                if time.time() - start_time > self.timeout:
                    try:
                        os.close(self.fd)
                    except Exception:
                        pass
                    raise TimeoutError(f"Timeout critique (>{self.timeout}s) : Contention excessive sur le verrou OS natif.")

                attempt += 1
                # Backoff exponentiel + jitter pour lisser l'accès concurrent massif
                sleep_time = min(0.01 * (1.4**attempt), 0.15) + random.uniform(0.002, 0.01)
                time.sleep(sleep_time)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.fd is not None:
            try:
                if sys.platform == "win32":
                    import msvcrt

                    os.lseek(self.fd, 0, os.SEEK_SET)
                    try:
                        msvcrt.locking(self.fd, msvcrt.LK_UNLCK, 1)
                    except Exception:
                        pass
                else:
                    import fcntl

                    fcntl.flock(self.fd, fcntl.LOCK_UN)
            except Exception:
                pass
            try:
                os.close(self.fd)
            except Exception:
                pass
