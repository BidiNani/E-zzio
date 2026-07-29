from runtime.memory.semantic.health_monitor import MemoryHealth
from runtime.memory.semantic.corruption_detector import MemoryCorruptionDetector
from runtime.memory.semantic.memory_checkpoint import MemoryCheckpoint
from runtime.memory.semantic.auto_repair import MemoryRepair



class SelfHealingMemory:


    def __init__(self):

        self.checkpoint=MemoryCheckpoint()



    def process(self,experiences,memory):


        self.checkpoint.create(
            memory
        )


        health=MemoryHealth.check(
            experiences
        )


        corrupted=MemoryCorruptionDetector.detect(
            experiences
        )


        if corrupted or not health["healthy"]:

            return {
                "status":"RECOVERY",
                "repair":
                    MemoryRepair.repair()
            }


        return {

            "status":"HEALTHY",

            "health":
                health,

            "checkpoint":
                True
        }
