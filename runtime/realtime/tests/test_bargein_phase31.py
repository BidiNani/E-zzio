import asyncio
import bootstrap
from runtime.realtime.voice import BargeInController

async def run():
    controller = BargeInController()

    # Test 1 : Single interruption + Telemetry Audit Event
    req_id = "req-audit-01"
    token = await controller.register(req_id)
    assert not await controller.is_interrupted(req_id)

    await controller.interrupt(req_id, source="USER", reason="BARGE_IN_TRIGGER")
    
    assert await controller.is_interrupted(req_id)
    assert token.is_cancelled()
    
    event = await controller.get_event(req_id)
    assert event is not None
    assert event.source == "USER"
    assert event.reason == "BARGE_IN_TRIGGER"
    
    await controller.unregister(req_id)

    # Test 2 : Concurrent sessions (10 streams)
    ids = [f"stress-{i}" for i in range(10)]
    for rid in ids:
        await controller.register(rid)

    await asyncio.gather(*(controller.interrupt(rid, source="SYSTEM", reason="BATCH_FLUSH") for rid in ids))

    for rid in ids:
        assert await controller.is_interrupted(rid)
        ev = await controller.get_event(rid)
        assert ev.source == "SYSTEM"
        await controller.unregister(rid)

    # Test 3 : Lifecycle Reset & Recovery
    reuse_id = "lifecycle-99"
    await controller.register(reuse_id)
    await controller.interrupt(reuse_id)
    assert await controller.is_interrupted(reuse_id)
    await controller.unregister(reuse_id)

    t_new = await controller.register(reuse_id)
    assert not await controller.is_interrupted(reuse_id)
    assert await controller.get_event(reuse_id) is None
    await controller.unregister(reuse_id)

if __name__ == "__main__":
    asyncio.run(run())
