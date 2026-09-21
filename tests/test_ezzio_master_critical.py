"""Tests core/ezzio_master.py : EzzioMaster import + API."""
import pytest


def test_ezzio_master_importable():
    from core.ezzio_master import EzzioMaster
    assert EzzioMaster is not None


def test_ezzio_master_instantiates():
    from core.ezzio_master import EzzioMaster
    m = EzzioMaster()
    assert m is not None
    assert hasattr(m, "provider")


def test_ezzio_master_has_process_chat():
    from core.ezzio_master import EzzioMaster
    assert hasattr(EzzioMaster, "process_chat")


def test_ezzio_master_has_process_user_message():
    from core.ezzio_master import EzzioMaster
    assert hasattr(EzzioMaster, "process_user_message")


def test_ezzio_master_has_memory():
    from core.ezzio_master import EzzioMaster
    m = EzzioMaster()
    assert hasattr(m, "memory")
