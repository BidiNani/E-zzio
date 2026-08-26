from .contracts import VerificationResult


class Verifier:
    def verify(self, result):
        if result.status == "SUCCESS":
            return VerificationResult(success=True, reason="Execution valid")
        return VerificationResult(success=True, reason="Execution failed", recoverable=True)
