import hashlib
import hmac


class MemoryIntegrity:


    KEY=b"EZZIO_MEMORY_CORE"


    @classmethod
    def sign(cls,data):

        return hmac.new(
            cls.KEY,
            data.encode("utf8"),
            hashlib.sha256
        ).hexdigest()


    @classmethod
    def verify(
        cls,
        data,
        signature
    ):

        return (
            cls.sign(data)
            ==
            signature
        )
