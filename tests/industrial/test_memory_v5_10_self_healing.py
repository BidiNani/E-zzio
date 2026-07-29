
from runtime.memory.semantic.health_monitor import MemoryHealth
from runtime.memory.semantic.corruption_detector import MemoryCorruptionDetector
from runtime.memory.semantic.memory_checkpoint import MemoryCheckpoint
from runtime.memory.semantic.auto_repair import MemoryRepair
from runtime.memory.semantic.self_healing_core import SelfHealingMemory



def test_health_ok():

    result=MemoryHealth.check(
        [
            {"score":100}
        ]
    )

    assert result["healthy"]



def test_health_fail():

    result=MemoryHealth.check(
        [
            {"bad":100}
        ]
    )

    assert result["healthy"] == False



def test_corruption():

    assert (
        MemoryCorruptionDetector.detect(
            None
        )
    )



def test_checkpoint():

    c=MemoryCheckpoint()

    c.create(
        {
            "value":1
        }
    )

    assert (
        c.restore()["value"]
        ==
        1
    )



def test_repair():

    result=MemoryRepair.repair()

    assert (
        result["status"]
        ==
        "REPAIRED"
    )



def test_self_healing():

    result=SelfHealingMemory().process(
        [
            {"score":100}
        ],
        {}
    )

    assert (
        result["status"]
        ==
        "HEALTHY"
    )



def test_self_recovery():

    result=SelfHealingMemory().process(
        None,
        {}
    )

    assert (
        result["status"]
        ==
        "RECOVERY"
    )

