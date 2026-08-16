import sys
import time
from pathlib import Path

# S'assure que le dossier parent (v458) est dans le PYTHONPATH
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

try:
    from concurrent_segmented_engine import ConcurrentSegmentedEngine
    engine = ConcurrentSegmentedEngine(str(current_dir))
    i = 0
    while True:
        engine.write_event({"crash_seq": i, "payload": "live_chaos_data"})
        i += 1
        time.sleep(0.001)
except Exception as e:
    print(f"[WORKER ERREUR] {e}", file=sys.stderr)
    sys.exit(1)
