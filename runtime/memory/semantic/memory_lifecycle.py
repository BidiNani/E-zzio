class MemoryLifecycle:


    @staticmethod
    def state(weight):


        states={

            "CRITICAL":
                "VALIDATED",

            "HIGH":
                "CONSOLIDATED",

            "MEDIUM":
                "LEARNING",

            "LOW":
                "ARCHIVED"
        }


        return states.get(
            weight,
            "UNKNOWN"
        )
