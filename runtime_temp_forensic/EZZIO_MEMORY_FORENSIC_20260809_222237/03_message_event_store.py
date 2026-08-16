from runtime.core.message import Message
from runtime.memory.events import RuntimeEvent
from runtime.memory.sqlite.store import SQLiteEventStore
import uuid

print("[START] canonical chain test")

store = SQLiteEventStore(":memory:")

sid = "chain_" + uuid.uuid4().hex

msg = Message(
    role="user",
    content="FORENSIC_CHAIN_TEST",
    source="validation"
)

print(f"MESSAGE={msg.to_dict()}")

event = RuntimeEvent(
    event_type="message",
    session_id=sid,
    actor=msg.role,
    payload=msg.to_dict(),
    trace_id=sid
)

print(f"EVENT={event.to_dict()}")

store.append_event(event)

rows = store.get_events_by_session(sid)

print(f"ROWS={len(rows)}")

if rows:
    print(f"PAYLOAD={rows[0]['payload']}")

expected = {
    "role": "user",
    "content": "FORENSIC_CHAIN_TEST",
    "source": "validation"
}

if (
    len(rows) == 1
    and rows[0]["payload"]["role"] == expected["role"]
    and rows[0]["payload"]["content"] == expected["content"]
    and rows[0]["payload"]["source"] == expected["source"]
    and rows[0]["session_id"] == sid
    and rows[0]["trace_id"] == sid
):
    print("RESULT=PASS")
else:
    print("RESULT=FAIL")

store.close()
