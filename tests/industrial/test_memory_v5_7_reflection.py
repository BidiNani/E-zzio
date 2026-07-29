from runtime.memory.semantic.reflection_engine import MemoryReflection
from runtime.memory.semantic.maturity import MemoryMaturity
from runtime.memory.semantic.recommendation import MemoryRecommendation
from runtime.memory.semantic.reflection_core import ReflectionCore


def test_reflection():

    r=MemoryReflection.analyze(
        [
            {"score":100},
            {"score":80}
        ]
    )

    assert r["trend"]=="POSITIVE"



def test_maturity():

    score=MemoryMaturity.calculate(
        {
            "count":2,
            "average":90,
            "trend":"POSITIVE"
        }
    )

    assert score==100



def test_recommendation():

    r=MemoryRecommendation.generate(
        {
            "trend":"POSITIVE"
        }
    )

    assert r["action"]=="REINFORCE"



def test_core():

    result=ReflectionCore().evaluate(
        [
            {"score":100}
        ]
    )

    assert "maturity" in result
