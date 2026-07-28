import os
import tempfile

class OutputGuard:
    """Protège contre les deadlocks PIPE et l'épuisement du disque (Watchdog Actif)."""
    def __init__(self, max_bytes=1024*1024*2): # 2 Mo max
        self.max_bytes = max_bytes
        self.stdout_fd, self.stdout_path = tempfile.mkstemp(prefix="ezzio_out_")
        self.stderr_fd, self.stderr_path = tempfile.mkstemp(prefix="ezzio_err_")

    def get_fds(self):
        return self.stdout_fd, self.stderr_fd
        
    def check_size_limits(self):
        """Watchdog appelé pendant la boucle de supervision."""
        try:
            if os.path.exists(self.stdout_path) and os.path.getsize(self.stdout_path) > self.max_bytes:
                raise InterruptedError("STDOUT Limit Exceeded (> 2MB).")
            if os.path.exists(self.stderr_path) and os.path.getsize(self.stderr_path) > self.max_bytes:
                raise InterruptedError("STDERR Limit Exceeded (> 2MB).")
        except OSError:
            pass

    def collect_and_cleanup(self) -> tuple[str, str]:
        stdout_content = self._read_and_truncate(self.stdout_path)
        stderr_content = self._read_and_truncate(self.stderr_path)
        try:
            os.remove(self.stdout_path)
            os.remove(self.stderr_path)
        except Exception:
            pass
        return stdout_content, stderr_content

    def _read_and_truncate(self, filepath: str) -> str:
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(self.max_bytes + 1)
                if len(content) > self.max_bytes:
                    return content[:self.max_bytes] + "\n...[TRUNCATED BY OUTPUT GUARD]..."
                return content
        except Exception as e:
            return f"[OutputGuard Error: {str(e)}]"