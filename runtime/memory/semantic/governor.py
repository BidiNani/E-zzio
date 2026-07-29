from runtime.memory.semantic.policy import MemoryPolicy
from runtime.memory.semantic.trust_score import MemoryTrust


class MemoryGovernor:


    def evaluate(self,memory):


        score=MemoryTrust.calculate(
            integrity=
                memory.get(
                    "integrity",
                    True
                ),
            confirmations=
                memory.get(
                    "confirmations",
                    0
                )
        )


        return {

            "score":
                score,

            "decision":
                MemoryPolicy.action(
                    score
                )

        }
