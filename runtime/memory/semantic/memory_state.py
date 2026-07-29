class MemoryState:


    def __init__(self):

        self.state={
            "health":0,
            "maturity":0,
            "learning":False,
            "trend":"UNKNOWN",
            "last_action":"NONE"
        }



    def update(
        self,
        maturity,
        trend,
        learning,
        action
    ):

        self.state.update({

            "health":
                min(
                    maturity,
                    100
                ),

            "maturity":
                maturity,

            "learning":
                learning,

            "trend":
                trend,

            "last_action":
                action
        })


        return self.state
