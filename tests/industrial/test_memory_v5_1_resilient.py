from runtime.memory.semantic.atomic_storage import AtomicStorage
from runtime.memory.semantic.backup_rotation import BackupRotation
from runtime.memory.semantic.sentinel import MemorySentinel
from runtime.memory.semantic.events import MemoryEvents
from runtime.memory.semantic.telemetry import MemoryTelemetry


def test_atomic(tmp_path):

    f=tmp_path/"memory.json"

    AtomicStorage.write_json(
        str(f),
        {"ok":True}
    )

    assert f.exists()



def test_event():

    e=MemoryEvents.event(
        "TEST"
    )

    assert e["event"]=="TEST"



def test_telemetry():

    t=MemoryTelemetry()

    t.record(
        "health",
        1
    )

    assert "health" in t.export()["metrics"]



def test_sentinel():

    s=MemorySentinel()

    assert "health" in s.check()
