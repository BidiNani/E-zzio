class MemoryCoherence:


    @staticmethod
    def calculate(items):

        if not items:
            return 0


        return min(
            100,
            len(items)*10
        )
