class MemoryWeight:


    @staticmethod
    def calculate(
        trust=0,
        confirmations=0,
        usage=0
    ):

        score=0


        score += min(
            trust,
            50
        )


        score += min(
            confirmations*5,
            30
        )


        score += min(
            usage*2,
            20
        )


        # normalization adaptive
        if (
            trust >= 50
            and confirmations >= 5
            and usage >= 5
        ):
            return 100


        return min(
            score,
            100
        )
