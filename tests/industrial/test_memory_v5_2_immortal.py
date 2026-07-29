from runtime.memory.semantic.wal import MemoryWAL
from runtime.memory.semantic.integrity import MemoryIntegrity
from runtime.memory.semantic.score import MemoryScore


def test_wal(tmp_path):

    wal=MemoryWAL(
        str(tmp_path/"x.wal")
    )

    wal.append(
        "WRITE",
        {"a":1}
    )

    assert len(
        wal.replay()
    )==1



def test_integrity():

    data="memory"

    sig=MemoryIntegrity.sign(
        data
    )

    assert MemoryIntegrity.verify(
        data,
        sig
    )



def test_score():

    s=MemoryScore.calculate()

    assert s["memory_health"]==100
