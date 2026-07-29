class MemoryHealth:

    @staticmethod
    def check(experiences):

        if experiences is None:
            return {
                "healthy":False,
                "reason":"NULL_MEMORY"
            }


        for item in experiences:

            if "score" not in item:
                return {
                    "healthy":False,
                    "reason":"MISSING_SCORE"
                }


            if not isinstance(
                item["score"],
                (int,float)
            ):
                return {
                    "healthy":False,
                    "reason":"INVALID_SCORE"
                }


        return {
            "healthy":True,
            "reason":"OK"
        }
