
from runtime.memory.semantic.memory_consolidator import MemoryConsolidator
from runtime.memory.semantic.memory_weight import MemoryWeight
from runtime.memory.semantic.memory_lifecycle import MemoryLifecycle
from runtime.memory.semantic.intelligent_repair import IntelligentRepair
from runtime.memory.semantic.consolidation_core import ConsolidationCore



def test_consolidation():

    result=MemoryConsolidator.consolidate(
        [
            {"score":100},
            {"score":90}
        ]
    )

    assert result["status"]=="CONSOLIDATED"



def test_confidence():

    result=MemoryConsolidator.consolidate(
        [
            {"score":100},
            {"score":80}
        ]
    )

    assert result["confidence"]==90



def test_weight():

    assert (
        MemoryWeight.calculate(95)
        ==
        "CRITICAL"
    )



def test_lifecycle():

    assert (
        MemoryLifecycle.state(
            "HIGH"
        )
        ==
        "CONSOLIDATED"
    )



def test_repair():

    result=IntelligentRepair.rebuild(
        None
    )

    assert (
        result["status"]
        ==
        "REBUILT"
    )



def test_core():

    result=ConsolidationCore().consolidate(
        [
            {"score":100}
        ]
    )

    assert (
        "lifecycle"
        in result
    )

