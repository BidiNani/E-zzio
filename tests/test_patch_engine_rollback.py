"""tests/test_patch_engine_rollback.py — Regression test for PatchEngine.rollback prefix collision bug."""
import os
import tempfile
import time

from core.agent.patch_engine import PatchEngine


def test_rollback_prefix_isolation():
    tmp_dir = tempfile.mkdtemp()
    pe = PatchEngine(tmp_dir)

    file_a = os.path.join(tmp_dir, "core", "test")
    os.path.join(tmp_dir, "core", "test_extra")

    pe.write_file("core/test_extra", "CONTENT_EXTRA_v1")
    pe.write_file("core/test_extra", "CONTENT_EXTRA_v2")
    time.sleep(0.01)

    pe.write_file("core/test", "CONTENT_TEST_v1")
    pe.write_file("core/test", "CONTENT_TEST_v2")

    success = pe.rollback("core/test")
    assert success is True

    with open(file_a, encoding="utf-8") as f:
        restored = f.read()

    assert restored == "CONTENT_TEST_v1", f"Expected CONTENT_TEST_v1, got {restored}"
