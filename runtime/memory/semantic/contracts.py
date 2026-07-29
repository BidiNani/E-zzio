import os
import json
import tempfile
import shutil
from datetime import datetime
from typing import List, Optional
from threading import Lock

from pydantic import BaseModel, Field


MEMORY_DIR = "runtime/memory"
MEMORY_FILE = os.path.join(MEMORY_DIR, "working_memory.json")
LOG_FILE = "infrastructure/discord_actions.log"


_MEMORY_LOCK = Lock()


class MemoryInteraction(BaseModel):
    timestamp: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    user_id: str
    action: str
    details: str
    sentiment: Optional[str] = "neutral"


class WorkingMemorySchema(BaseModel):
    version: str = "3.1-SemanticCore"
    last_sync: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    interactions: List[MemoryInteraction] = Field(default_factory=list)



class SemanticMemoryManager:

    def __init__(self):
        self._ensure_storage()


    def _ensure_storage(self):

        os.makedirs(MEMORY_DIR, exist_ok=True)

        log_dir = os.path.dirname(LOG_FILE)

        if log_dir:
            os.makedirs(log_dir, exist_ok=True)


        if not os.path.exists(MEMORY_FILE):
            self._save_raw(
                WorkingMemorySchema().model_dump()
            )


    def _load_raw(self):

        try:

            with open(
                MEMORY_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

            return WorkingMemorySchema(
                **data
            ).model_dump()


        except Exception:

            recovery = WorkingMemorySchema()

            self._save_raw(
                recovery.model_dump()
            )

            return recovery.model_dump()



    def _save_raw(self, data):

        with _MEMORY_LOCK:

            directory = os.path.dirname(MEMORY_FILE)

            os.makedirs(
                directory,
                exist_ok=True
            )


            fd, temp_path = tempfile.mkstemp(
                prefix="memory_",
                suffix=".tmp",
                dir=directory
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


                if os.path.exists(MEMORY_FILE):

                    shutil.copy2(
                        MEMORY_FILE,
                        MEMORY_FILE + ".bak"
                    )


                os.replace(
                    temp_path,
                    MEMORY_FILE
                )


            finally:

                if os.path.exists(temp_path):

                    os.remove(temp_path)



    def record_interaction(
        self,
        user_id: str,
        action: str,
        details: str,
        sentiment: str = "neutral"
    ) -> bool:


        try:

            interaction = MemoryInteraction(
                user_id=str(user_id),
                action=action,
                details=details,
                sentiment=sentiment
            )


            mem_data = self._load_raw()


            mem_data["interactions"].append(
                interaction.model_dump()
            )


            if len(mem_data["interactions"]) > 100:

                mem_data["interactions"] = (
                    mem_data["interactions"][-100:]
                )


            mem_data["last_sync"] = (
                datetime.now()
                .strftime("%Y-%m-%d %H:%M:%S")
            )


            self._save_raw(
                mem_data
            )


            with open(
                LOG_FILE,
                "a",
                encoding="utf-8"
            ) as lf:

                lf.write(
                    f"[{interaction.timestamp}] "
                    f"[USER:{interaction.user_id}] "
                    f"[{interaction.sentiment}] "
                    f"{interaction.action} -> "
                    f"{interaction.details}\n"
                )


            return True


        except Exception as e:

            print(
                f"[-] SemanticMemory failure : {e}"
            )

            return False



memory_core = SemanticMemoryManager()
