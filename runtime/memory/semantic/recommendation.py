class MemoryRecommendation:


    @staticmethod
    def generate(reflection):

        if reflection["trend"]=="POSITIVE":

            return {
                "action":"REINFORCE",
                "priority":"HIGH"
            }


        if reflection["trend"]=="STABLE":

            return {
                "action":"MONITOR",
                "priority":"MEDIUM"
            }


        return {
            "action":"REVIEW",
            "priority":"HIGH"
        }
