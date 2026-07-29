class MemoryRecovery:


    def __init__(self):

        self.rollback=False



    def restore(self):

        self.rollback=True

        return {

            "status":
                "ROLLBACK",

            "recovered":
                True

        }
