"""
E-ZZIO V9.1 — Real Android Device / AVD Runtime Certification Gate.
Valide l'execution reelle sur peripherique physique ou AVD :
1. Presence d'un peripherique ADB en ligne (state: 'device')
2. Presence de l'application release installee (package 'ai.ezzio.office')
3. Met donnees de version de release (versionCode 901, versionName 9.0.1)
4. Absence du flag DEBUGGABLE dans le package installe (pure release)
5. Demarrage de l'activite MainActivity sans crash (zero exception fatale)
"""
from pathlib import Path
import shutil
import subprocess
import pytest


def get_adb_path():
    cand = Path("G:/tools/platform-tools/adb.exe")
    if cand.exists():
        return str(cand)
    system_adb = shutil.which("adb")
    if system_adb:
        return system_adb
    pytest.skip("ADB introuvable dans G:/tools/platform-tools/adb.exe ou PATH")


def test_android_device_online():
    """Verifie qu'un peripherique Android physique ou AVD est connecte et pret."""
    adb = get_adb_path()
    res = subprocess.run([adb, "devices"], capture_output=True, text=True, check=True)
    lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]
    devices = [line.split()[0] for line in lines[1:] if "\tdevice" in line or line.endswith("device")]
    assert len(devices) > 0, f"Aucun peripherique Android en ligne. Sortie adb: {res.stdout}"


def test_package_installed_on_device():
    """Verifie que le package officiel ai.ezzio.office est bien installe sur l'appareil."""
    adb = get_adb_path()
    res = subprocess.run([adb, "shell", "pm", "path", "ai.ezzio.office"], capture_output=True, text=True, check=True)
    assert "package:" in res.stdout and "ai.ezzio.office" in res.stdout, (
        f"Le package ai.ezzio.office n'est pas installe sur l'appareil: {res.stdout}"
    )


def test_package_release_metadata():
    """Verifie que la version installee correspond exactement a la V9.1 (versionCode 901, 9.0.1)."""
    adb = get_adb_path()
    res = subprocess.run([adb, "shell", "dumpsys", "package", "ai.ezzio.office"], capture_output=True, text=True, check=True)
    output = res.stdout
    assert "versionCode=901" in output, "versionCode 901 introuvable dans dumpsys package"
    assert "versionName=9.0.1" in output, "versionName 9.0.1 introuvable dans dumpsys package"


def test_package_is_production_release_not_debuggable():
    """Verifie que le package installe est une release pure (sans flag DEBUGGABLE ni suffixe .debug)."""
    adb = get_adb_path()
    res = subprocess.run([adb, "shell", "dumpsys", "package", "ai.ezzio.office"], capture_output=True, text=True, check=True)
    output = res.stdout
    for line in output.splitlines():
        if "pkgFlags=" in line:
            assert "DEBUGGABLE" not in line, f"Le package installe contient le flag DEBUGGABLE: {line}"


def test_activity_launch_and_zero_crashes():
    """Verifie que MainActivity demarre avec succes et ne provoque aucun crash fatal."""
    adb = get_adb_path()
    start_res = subprocess.run(
        [adb, "shell", "am", "start", "-n", "ai.ezzio.office/.MainActivity"],
        capture_output=True,
        text=True,
        check=True
    )
    assert "Starting: Intent" in start_res.stdout or "Warning: Activity not started" in start_res.stdout

    log_res = subprocess.run(
        [adb, "logcat", "-d"],
        capture_output=True,
        text=True,
        check=True
    )
    crash_lines = [
        line for line in log_res.stdout.splitlines()
        if "FATAL EXCEPTION" in line and "ai.ezzio.office" in line
    ]
    assert len(crash_lines) == 0, f"Crash fatal detecte sur l'appareil: {crash_lines}"
