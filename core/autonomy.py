import socket
import subprocess


def check_port(host: str = "127.0.0.1", port: int = 11434) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        result = s.connect_ex((host, port))
        return result == 0
    except Exception:
        return False
    finally:
        s.close()


def check_ollama() -> bool:
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, check=False)
        return result.returncode == 0
    except Exception:
        return False
