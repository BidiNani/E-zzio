import pytest

from tools.fs_tools import observe_filesystem


def test_phase9_filesystem_physical_count_core():
    obs = observe_filesystem("core")
    assert obs["status"] == "SUCCESS"
    py_files = [f for f in obs["files"].keys() if f.endswith(".py")]
    # Vérification physique réelle
    assert len(py_files) >= 200
    assert "actions.py" in [f.split("/")[-1] for f in py_files]

def test_phase9_security_fail_closed_guarantee():
    res = observe_filesystem("../../../Windows/System32")
    assert res["status"] == "DENIED"
