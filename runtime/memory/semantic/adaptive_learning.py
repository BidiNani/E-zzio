from runtime.memory.semantic.weight_engine import MemoryWeight


class AdaptiveLearning:


    def evaluate(
        self,
        memory
    ):

        weight=MemoryWeight.calculate(
            memory.get(
                "trust",
                0
            ),
            memory.get(
                "confirmations",
                0
            ),
            memory.get(
                "usage",
                0
            )
        )


        return {

            "weight":
                weight,

            "adaptive":
                weight >= 50
        }
