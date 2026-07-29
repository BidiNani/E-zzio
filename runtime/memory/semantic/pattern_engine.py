class MemoryPattern:


    @staticmethod
    def normalize(memory):

        return str(memory).lower().strip()



    @staticmethod
    def similarity(a,b):

        x=set(
            MemoryPattern.normalize(a).split()
        )

        y=set(
            MemoryPattern.normalize(b).split()
        )

        if not x or not y:
            return 0


        return int(
            len(x & y)
            /
            len(x | y)
            *
            100
        )
