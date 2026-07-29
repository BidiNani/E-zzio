class MemoryReward:


    @staticmethod
    def calculate(success):


        if success:
            return 100


        return -50



    @staticmethod
    def classify(score):

        if score>=80:
            return "SUCCESS"


        if score>=0:
            return "NEUTRAL"


        return "FAILURE"
