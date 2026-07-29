class MemoryAdaptation:


    def adjust(
        self,
        experiences
    ):

        if not experiences:

            return {
                "adaptation":0
            }


        total=sum(
            x["score"]
            for x in experiences
        )


        average=total / len(experiences)


        return {

            "experience_count":
                len(experiences),

            "average_score":
                average,

            "learning":
                average > 50
        }
