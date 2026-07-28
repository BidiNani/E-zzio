from collections import deque


class ExecutionScheduler:

    def __init__(self):

        self.queue = deque()

    def push(self, execution):

        self.queue.append(execution)

    def next(self):

        if self.queue:
            return self.queue.popleft()

        return None
