"""E-ZZIO Dispatcher — Délégataire vers EzzioMaster de délégation pure."""
from __future__ import annotations
from typing import Any, Dict
from core.ezzio_master import ezzio_master


class IntentDispatcher:
    async def dispatch_async(
        self,
        text: str,
        session_id: str = "",
        speed: str = "fast",
        force_cloud: bool = True
    ) -> Dict[str, Any]:
        return await ezzio_master.execute_intent(
            user_prompt=text,
            speed=speed,
            force_cloud=force_cloud,
            session_id=session_id
        )

    def dispatch(
        self,
        text: str,
        session_id: str = "",
        speed: str = "fast",
        force_cloud: bool = True
    ) -> Dict[str, Any]:
        import asyncio
        return asyncio.run(self.dispatch_async(text, session_id, speed, force_cloud))


dispatcher = IntentDispatcher()


def dispatch(text: str, session_id: str = "", speed: str = "fast", force_cloud: bool = True) -> Dict[str, Any]:
    return dispatcher.dispatch(text=text, session_id=session_id, speed=speed, force_cloud=force_cloud)


