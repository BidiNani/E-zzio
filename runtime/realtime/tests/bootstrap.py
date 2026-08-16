import sys
from pathlib import Path

# Résolution absolue de la racine E-ZZIO (G:\AI\E-zzio)
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
