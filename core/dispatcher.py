"""E-ZZIO Dispatcher — Délégataire tolérant et sécurisé vers EzzioMaster."""
from __future__ import annotations
from typing import Any, Dict
from core.ezzio_master import ezzio_master


class IntentDispatcher:
    async def dispatch_async(
        self,
        text: str,
        session_id: str = "",
        speed: str = "fast",
        force_cloud: bool = False,
        system_prompt: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        # system_prompt et kwargs sont acceptés pour compatibilité mais ignorés (CanonicalIdentity fait foi)
        return await ezzio_master.execute_intent(
            user_prompt=text,
            speed=speed,
            force_cloud=force_cloud,
            session_id=session_id,
            **kwargs
        )

    def dispatch(
        self,
        text: str,
        session_id: str = "",
        speed: str = "fast",
        force_cloud: bool = False,
        system_prompt: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        import asyncio
        return asyncio.run(self.dispatch_async(text, session_id, speed, force_cloud, system_prompt=system_prompt, **kwargs))


dispatcher = IntentDispatcher()


def dispatch(text: str, session_id: str = "", speed: str = "fast", force_cloud: bool = False, system_prompt: str = "", **kwargs) -> Dict[str, Any]:
    return dispatcher.dispatch(text=text, session_id=session_id, speed=speed, force_cloud=force_cloud, system_prompt=system_prompt, **kwargs)


# Alias canonique requis par EzzioMaster
ezzio_dispatcher = dispatcher

