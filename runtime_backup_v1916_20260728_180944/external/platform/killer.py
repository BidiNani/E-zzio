import os
import subprocess
import time

class ProcessKiller:
    """Abstraction OS pour un arrêt des processus propre (SIGTERM -> Grace -> SIGKILL Tree)."""
    
    @staticmethod
    def terminate(process, graceful_timeout: float = 2.0):
        if not process or process.poll() is not None:
            return # Déjà terminé

        try:
            process.terminate() # Demande courtoise (SIGTERM)
        except Exception:
            pass

        # Délai de grâce
        start_t = time.time()
        while process.poll() is None and (time.time() - start_t) < graceful_timeout:
            time.sleep(0.05)

        # Si toujours vivant après délai de grâce : Hard Kill (Process Tree)
        if process.poll() is None:
            if os.name == 'nt':
                try:
                    # Windows : force l'arrêt de tout l'arbre de processus pour éviter les zombies
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)], capture_output=True)
                except Exception:
                    pass
            try:
                process.kill() # Ultime tentative standard
            except Exception:
                pass