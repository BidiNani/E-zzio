import pytest
from v17.events.buffer import EventBuffer
from v17.events.models import EventSeverity

def test_v17_2_event_publish_and_bounded():
    buf = EventBuffer(max_size=5)
    for i in range(10):
        buf.publish(f"test.event.{i}", "test_source", {"count": i})
    events = buf.get_recent(10)
    assert len(events) == 5
    assert events[0].event_type == "test.event.9"

def test_v17_2_event_subscription():
    buf = EventBuffer(max_size=10)
    received = []
    def callback(evt):
        received.append(evt.event_type)
    buf.subscribe(callback)
    buf.publish("task.created", "test", {"id": "t1"})
    assert len(received) == 1
    assert received[0] == "task.created"
    buf.unsubscribe(callback)
    buf.publish("task.finished", "test", {"id": "t1"})
    assert len(received) == 1
