from runtime.memory.semantic.governor import MemoryGovernor
from runtime.memory.semantic.policy import MemoryPolicy
from runtime.memory.semantic.trust_score import MemoryTrust


def test_trust():

    score=MemoryTrust.calculate(
        True,
        10,
        5
    )

    assert score>50



def test_policy():

    assert (
        MemoryPolicy.action(90)
        ==
        "KEEP"
    )



def test_governor():

    g=MemoryGovernor()

    result=g.evaluate(
        {
            "integrity":True,
            "confirmations":10
        }
    )

    assert "decision" in result
