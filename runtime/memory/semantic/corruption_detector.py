class MemoryCorruptionDetector:


    @staticmethod
    def detect(experiences):

        health = experiences is not None


        if not health:
            return True


        for item in experiences:

            if not isinstance(item,dict):
                return True


        return False
