from runtime.memory.semantic.crypto import MemoryCrypto
from runtime.memory.semantic.self_healing import MemorySelfHealing
from runtime.memory.semantic.health import MemoryHealth

import json


def test_checksum():

    data={
        "hello":"world"
    }

    checksum=MemoryCrypto.checksum(data)

    assert MemoryCrypto.verify(
        data,
        checksum
    )



def test_health():

    report=MemoryHealth.report()

    assert "overall" in report



def test_self_healing(tmp_path):

    memory_file=tmp_path/"memory.json"

    memory_file.write_text(
        "{broken",
        encoding="utf8"
    )


    healer=MemorySelfHealing(
        str(memory_file)
    )


    assert healer.validate_cache()


    repaired=json.loads(
        memory_file.read_text(
            encoding="utf8"
        )
    )


    assert (
        "interactions"
        in
        repaired
    )
