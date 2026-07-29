from runtime.memory.semantic.memory_orchestrator import MemoryOrchestrator


class MemoryCycle:


    def execute(
        self,
        experiences
    ):

        return MemoryOrchestrator().run(
            experiences
        )
