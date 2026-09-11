import pytest
import subprocess
import sys
from pathlib import Path

def test_operational_startup_script_execution():
    root = Path(__file__).resolve().parent.parent
    start_script = root / "scripts" / "start_ezzio.py"
    
    proc = subprocess.run([sys.executable, str(start_script)], capture_output=True, text=True)
    assert proc.returncode == 0
    assert "E-ZZIO READY" in proc.stdout
    assert "DEMARRAGE" in proc.stdout

def test_operational_stop_script_execution():
    root = Path(__file__).resolve().parent.parent
    stop_script = root / "scripts" / "stop_ezzio.py"
    
    proc = subprocess.run([sys.executable, str(stop_script)], capture_output=True, text=True)
    assert proc.returncode == 0
    assert "ARRET DU SYSTEME" in proc.stdout
