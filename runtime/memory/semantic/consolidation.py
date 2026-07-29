class MemoryConsolidation:


    THRESHOLD=70


    @classmethod
    def should_consolidate(
        cls,
        score
    ):

        return score >= cls.THRESHOLD



    @classmethod
    def consolidate(
        cls,
        memories
    ):

        return {
            "status":
                "CONSOLIDATED",

            "count":
                len(memories)
        }
