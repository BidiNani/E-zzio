class MemoryForgetting:


    LIMIT=20


    @staticmethod
    def decay(
        age,
        importance
    ):

        penalty=min(
            age,
            50
        )

        return max(
            0,
            importance-penalty
        )



    @classmethod
    def should_forget(
        cls,
        score
    ):

        return score < cls.LIMIT
