"""tests/test_operational_helper.py — Tests unitaires de validation du module operational_helper."""
from core.capabilities.operational_helper import compute_task_checksum, format_task_receipt


def test_compute_task_checksum():
    cs1 = compute_task_checksum("task-100", {"action": "build", "param": 1})
    cs2 = compute_task_checksum("task-100", {"param": 1, "action": "build"})
    assert len(cs1) == 16
    assert cs1 == cs2  # L'ordre des clés n'altère pas l'empreinte

    cs_empty = compute_task_checksum("task-100", None)
    assert len(cs_empty) == 16

    cs_unicode = compute_task_checksum("task-100", {"text": "téléométrie_éàç"})
    assert len(cs_unicode) == 16


def test_format_task_receipt():
    payload = {"action": "build"}
    receipt = format_task_receipt("task-100", "SUCCESS", payload)
    assert receipt["task_id"] == "task-100"
    assert receipt["status"] == "SUCCESS"
    assert len(receipt["checksum"]) == 16
    assert receipt["checksum"] == compute_task_checksum("task-100", payload)
    assert "timestamp_utc" in receipt
