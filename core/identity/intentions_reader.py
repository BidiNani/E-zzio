"""
E-ZZIO — Intentions Reader
Permet au système de charger et de rappeler les raisons profondes de sa création.
"""
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
INTENTIONS_PATH = ROOT_DIR / "config" / "intentions.md"

def read_intentions() -> str:
    if not INTENTIONS_PATH.exists():
        return "Aucun journal d'intentions trouvé."
    return INTENTIONS_PATH.read_text(encoding="utf-8")

if __name__ == "__main__":
    print(read_intentions())
