class OutputGuard:
    MAX_BYTES = 1024 * 512

    @staticmethod
    def sanitize(output: str) -> str:
        if not output:
            return ""
        encoded = output.encode("utf-8")
        if len(encoded) > OutputGuard.MAX_BYTES:
            truncated = encoded[:OutputGuard.MAX_BYTES].decode("utf-8", errors="ignore")
            return truncated + "\n...[TRUNCATED BY OUTPUT GUARD: MAX BYTE LIMIT REACHED]..."
        return output