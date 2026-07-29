from runtime.memory.semantic.memory_consolidator import MemoryConsolidator
from runtime.memory.semantic.memory_weight import MemoryWeight
from runtime.memory.semantic.memory_lifecycle import MemoryLifecycle
from runtime.memory.semantic.intelligent_repair import IntelligentRepair



class ConsolidationCore:


    def consolidate(self,experiences):


        result=MemoryConsolidator.consolidate(
            experiences
        )


        if result["status"]=="EMPTY":

            return result



        weight=MemoryWeight.calculate(
            result["confidence"]
        )


        return {

            "consolidation":
                result,

            "weight":
                weight,

            "lifecycle":
                MemoryLifecycle.state(
                    weight
                )

        }



    def repair(self,memory):

        return IntelligentRepair.rebuild(
            memory
        )
