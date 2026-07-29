from runtime.memory.semantic.memory_action import MemoryAction
from runtime.memory.semantic.memory_audit_bridge import MemoryAuditBridge
from runtime.memory.semantic.memory_recovery import MemoryRecovery



class MemoryExecutor:


    def __init__(self):

        self.audit=MemoryAuditBridge()
        self.recovery=MemoryRecovery()



    def execute(
        self,
        decision,
        memory
    ):


        try:


            action=MemoryAction.apply(
                decision
            )


            memory["last_action"]=action


            self.audit.record(
                action,
                "SUCCESS"
            )


            return {

                "action":
                    action,

                "status":
                    "EXECUTED",

                "memory":
                    memory

            }



        except Exception:


            return self.recovery.restore()
