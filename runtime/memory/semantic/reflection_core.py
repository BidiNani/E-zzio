from runtime.memory.semantic.reflection_engine import MemoryReflection
from runtime.memory.semantic.maturity import MemoryMaturity
from runtime.memory.semantic.recommendation import MemoryRecommendation


class ReflectionCore:


    def evaluate(self,experiences):


        reflection=MemoryReflection.analyze(
            experiences
        )


        return {

            "reflection":reflection,

            "maturity":
                MemoryMaturity.calculate(
                    reflection
                ),

            "recommendation":
                MemoryRecommendation.generate(
                    reflection
                )
        }
