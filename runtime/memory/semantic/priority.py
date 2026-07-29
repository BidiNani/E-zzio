class MemoryPriority:


    @staticmethod
    def calculate(
        trust,
        urgency,
        relevance
    ):

        return min(
            100,
            trust +
            urgency +
            relevance
        )
