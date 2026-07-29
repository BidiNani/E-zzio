class MemoryMaturity:


    @staticmethod
    def calculate(reflection):

        score=0


        if reflection["count"] > 0:
            score += 30


        if reflection["average"] >= 50:
            score += 40


        if reflection["trend"]=="POSITIVE":
            score += 30


        return min(
            score,
            100
        )
