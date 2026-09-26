"""Test de validation du module e2e_probe_target."""
from core.capabilities.e2e_probe_target import calculate_probe_hash


def test_calculate_probe_hash():
    res = calculate_probe_hash("ezzio_probe_test")
    assert len(res) == 12
    assert res == calculate_probe_hash("ezzio_probe_test")
