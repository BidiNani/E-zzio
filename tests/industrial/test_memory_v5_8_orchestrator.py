from runtime.memory.semantic.memory_cycle import MemoryCycle
from runtime.memory.semantic.memory_decision import MemoryDecision



def test_cycle():


    result=MemoryCycle().execute(
        [
            {"score":100},
            {"score":90}
        ]
    )


    assert result["maturity"]==100



def test_positive_decision():


    decision=MemoryDecision.decide(
        100,
        "POSITIVE"
    )


    assert decision=="REINFORCE"



def test_negative_decision():


    decision=MemoryDecision.decide(
        10,
        "NEGATIVE"
    )


    assert decision=="REVIEW"



def test_state():


    result=MemoryCycle().execute(
        [
            {"score":100}
        ]
    )


    assert (
        "state"
        in result
    )


def test_governance():


    result=MemoryCycle().execute(
        [
            {"score":100}
        ]
    )


    assert (
        result["decision"]
        ==
        "REINFORCE"
    )
