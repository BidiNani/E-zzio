import os


class MemoryLock:


    def __init__(
        self,
        path="runtime/memory/memory.lock"
    ):
        self.path=path


    def acquire(self):

        if os.path.exists(self.path):

            raise RuntimeError(
                "Memory locked"
            )


        open(
            self.path,
            "w"
        ).close()


    def release(self):

        if os.path.exists(
            self.path
        ):
            os.remove(
                self.path
            )
