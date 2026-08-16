
import sys
import time
from pathlib import Path

sys.path.insert(0, r'G:\AI\E-zzio')
from runtime.kernel.boot import EzzioBootloader

while not Path(r'G:\AI\E-zzio\runtime\kernel\v425_GO').exists():
    time.sleep(0.01)

b = EzzioBootloader()
if b._acquire_process_lock():
    Path(r'G:\AI\E-zzio\runtime\kernel\v425_results').joinpath('success_'+str(__import__('os').getpid())).touch()
