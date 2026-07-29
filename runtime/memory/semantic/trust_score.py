from datetime import datetime


class MemoryTrust:


    @staticmethod
    def calculate(
        integrity=True,
        age=0,
        confirmations=0
    ):

        score=0


        if integrity:
            score+=60


        score+=min(
            confirmations*5,
            30
        )


        if age < 86400:
            score+=10


        return min(
            score,
            100
        )


    @staticmethod
    def report(score):

        return {

            "score":score,

            "timestamp":
                datetime.now().isoformat()

        }
