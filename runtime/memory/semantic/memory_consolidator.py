class MemoryConsolidator:


    @staticmethod
    def consolidate(experiences):


        if not experiences:

            return {
                "status":"EMPTY",
                "confidence":0
            }



        scores=[
            x["score"]
            for x in experiences
        ]


        confidence=sum(scores)/len(scores)



        return {

            "status":
                "CONSOLIDATED",

            "count":
                len(scores),

            "confidence":
                confidence,

            "weight":
                "HIGH"
                if confidence >= 80
                else "MEDIUM"
        }
