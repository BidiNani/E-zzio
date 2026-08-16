class RetryGovernor:
    def __init__(self, max_retry=2):
        self.max_retry = max_retry
        self.count = 0

    def can_retry(self):
        if self.count >= self.max_retry:
            return False
        self.count += 1
        return True