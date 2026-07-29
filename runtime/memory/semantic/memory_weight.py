class MemoryWeight:


    @staticmethod
    def calculate(confidence):


        if confidence >= 90:
            return "CRITICAL"


        if confidence >= 70:
            return "HIGH"


        if confidence >= 40:
            return "MEDIUM"


        return "LOW"
