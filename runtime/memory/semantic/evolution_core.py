from runtime.memory.semantic.reward_engine import MemoryReward
from runtime.memory.semantic.adaptation_engine import MemoryAdaptation


class EvolutionCore:


    def evolve(
        self,
        experiences
    ):

        analysis=MemoryAdaptation().adjust(
            experiences
        )


        return {

            "status":
                "EVOLVED",

            "learning":
                analysis["learning"],

            "experience":
                analysis["experience_count"]
        }
