class RetryGovernor:
    """Gouverneur de retry borne pour la boucle agentique E-ZZIO."""

    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries
        self.retry_count = 0

    def can_retry(self) -> bool:
        if self.retry_count < self.max_retries:
            self.retry_count += 1
            return True
        return False

    def reset(self):
        self.retry_count = 0
