import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from runtime.memory.atomic_writer import AtomicEventWriter

if len(sys.argv) < 2:
    sys.exit(1)

target = sys.argv[1]
writer = AtomicEventWriter(target)
i = 1
while True:
    writer.write_event({"seq": i, "flood": True})
    i += 1
    time.sleep(0.01)
