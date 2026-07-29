from runtime.memory.semantic.experience_store import ExperienceStore
from runtime.memory.semantic.reward_engine import MemoryReward
from runtime.memory.semantic.adaptation_engine import MemoryAdaptation
from runtime.memory.semantic.evolution_core import EvolutionCore



def test_reward():

    assert (
        MemoryReward.calculate(True)
        ==
        100
    )



def test_store(tmp_path):

    s=ExperienceStore(
        str(tmp_path/"exp.json")
    )

    s.record(
        "test",
        "ok",
        100
    )

    assert len(
        s.load()
    )==1



def test_adaptation():

    result=MemoryAdaptation().adjust(
        [
            {
                "score":100
            },
            {
                "score":80
            }
        ]
    )

    assert result["learning"]



def test_evolution():

    result=EvolutionCore().evolve(
        [
            {
                "score":100
            }
        ]
    )

    assert result["status"]=="EVOLVED"
