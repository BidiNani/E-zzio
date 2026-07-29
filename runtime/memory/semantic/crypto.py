import hashlib
import json


class MemoryCrypto:

    @staticmethod
    def checksum(data:dict)->str:

        payload=json.dumps(
            data,
            sort_keys=True,
            ensure_ascii=False
        )

        return hashlib.sha256(
            payload.encode("utf-8")
        ).hexdigest()


    @staticmethod
    def verify(data:dict, expected:str)->bool:

        return (
            MemoryCrypto.checksum(data)
            ==
            expected
        )
