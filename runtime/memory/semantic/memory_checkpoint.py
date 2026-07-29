import copy


class MemoryCheckpoint:


    def __init__(self):

        self.snapshot=None



    def create(self,memory):

        self.snapshot=copy.deepcopy(memory)

        return self.snapshot



    def restore(self):

        return self.snapshot
