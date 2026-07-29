class MemoryMerge:


    @staticmethod
    def merge(old,new):

        result={}


        result.update(old)

        result.update(new)


        return result
