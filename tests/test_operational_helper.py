"""tests/test_operational_helper.py — Tests unitaires de validation du module operational_helper."""
from core.capabilities.operational_helper import compute_task_checksum, format_task_receipt


def test_compute_task_checksum():
    cs1 = compute_task_checksum("task-100", {"action": "build"})
    cs2 = compute_task_checksum("task-100", {"action": "build"})
    assert len(cs1) == 16
    assert cs1 == cs2


def test_format_task_receipt():
    receipt = format_task_receipt("task-100", "SUCCESS", {"action": "build"})
    assert receipt["task_id"] == "task-100"
    assert receipt["status"] == "SUCCESS"
    assert len(receipt["checksum"]) == 16
    assert "timestamp_utc" in receipt
