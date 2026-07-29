class MemoryAction:


    @staticmethod
    def apply(
        decision
    ):


        actions={

            "REINFORCE":
                "INCREASE_WEIGHT",

            "CONSOLIDATE":
                "LOCK_MEMORY",

            "REVIEW":
                "QUARANTINE",

            "FORGET":
                "DECREASE_WEIGHT"

        }


        return actions.get(
            decision,
            "NO_ACTION"
        )
