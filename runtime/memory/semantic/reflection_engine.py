class MemoryReflection:


    @staticmethod
    def analyze(experiences):

        if not experiences:
            return {
                "count":0,
                "average":0,
                "trend":"UNKNOWN"
            }


        scores=[
            x["score"]
            for x in experiences
        ]


        average=sum(scores)/len(scores)


        if average >= 80:
            trend="POSITIVE"

        elif average >= 50:
            trend="STABLE"

        else:
            trend="NEGATIVE"


        return {

            "count":
                len(scores),

            "average":
                average,

            "trend":
                trend
        }
