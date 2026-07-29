from runtime.memory.semantic.weight_engine import MemoryWeight
from runtime.memory.semantic.consolidation import MemoryConsolidation
from runtime.memory.semantic.forgetting import MemoryForgetting
from runtime.memory.semantic.priority import MemoryPriority
from runtime.memory.semantic.adaptive_learning import AdaptiveLearning



def test_weight():

    assert (
        MemoryWeight.calculate(
            50,
            5,
            5
        )
        ==
        100
    )



def test_consolidation():

    assert (
        MemoryConsolidation.should_consolidate(
            80
        )
    )



def test_forgetting():

    assert (
        MemoryForgetting.should_forget(
            10
        )
    )



def test_priority():

    assert (
        MemoryPriority.calculate(
            30,
            30,
            30
        )
        ==
        90
    )



def test_learning():

    result=AdaptiveLearning().evaluate(
        {
            "trust":50,
            "confirmations":2,
            "usage":5
        }
    )

    assert result["adaptive"]
