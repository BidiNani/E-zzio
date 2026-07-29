import os
import json
import tempfile


class AtomicStorage:


    @staticmethod
    def write_json(path,data):

        directory=os.path.dirname(path)

        os.makedirs(
            directory,
            exist_ok=True
        )


        fd,tmp=tempfile.mkstemp(
            dir=directory,
            prefix=".atomic_",
            suffix=".tmp"
        )


        try:

            with os.fdopen(
                fd,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    data,
                    f,
                    indent=4,
                    ensure_ascii=False
                )

                f.flush()
                os.fsync(
                    f.fileno()
                )


            os.replace(
                tmp,
                path
            )


        finally:

            if os.path.exists(tmp):
                os.remove(tmp)
