class MemoryDecision:


    @staticmethod
    def decide(
        maturity,
        trend
    ):


        if (
            maturity >= 80
            and trend=="POSITIVE"
        ):

            return "REINFORCE"



        if maturity < 30:

            return "REVIEW"



        if trend=="NEGATIVE":

            return "FORGET"



        return "MONITOR"
