from runtime.memory.semantic.reflection_engine import MemoryReflection
from runtime.memory.semantic.maturity import MemoryMaturity
from runtime.memory.semantic.recommendation import MemoryRecommendation
from runtime.memory.semantic.memory_decision import MemoryDecision
from runtime.memory.semantic.memory_state import MemoryState



class MemoryOrchestrator:


    def __init__(self):

        self.state=MemoryState()



    def run(
        self,
        experiences
    ):


        reflection=MemoryReflection.analyze(
            experiences
        )


        maturity=MemoryMaturity.calculate(
            reflection
        )


        recommendation=MemoryRecommendation.generate(
            reflection
        )


        decision=MemoryDecision.decide(
            maturity,
            reflection["trend"]
        )


        state=self.state.update(
            maturity,
            reflection["trend"],
            maturity>=50,
            decision
        )


        return {

            "reflection":
                reflection,

            "maturity":
                maturity,

            "recommendation":
                recommendation,

            "decision":
                decision,

            "state":
                state
        }
