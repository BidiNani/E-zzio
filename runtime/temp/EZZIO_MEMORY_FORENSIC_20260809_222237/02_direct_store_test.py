from runtime.memory.sqlite.store import SQLiteEventStore
from runtime.memory.events import RuntimeEvent
import uuid

print("[START] direct SQLite store test")

store = SQLiteEventStore(":memory:")

sid = "forensic_" + uuid.uuid4().hex
tid = "trace_" + uuid.uuid4().hex

print(f"SESSION={sid}")
print(f"TRACE={tid}")

event = RuntimeEvent(
    event_type="message",
    session_id=sid,
    actor="user",
    payload={
        "role": "user",
        "content": "FORENSIC_DIRECT_TEST",
        "source": "forensic"
    },
    trace_id=tid
)

print(f"EVENT_ID={event.event_id}")

store.append_event(event)

print("\n[READ ALL SESSION]")
rows = store.get_events_by_session(sid)

print(f"ROWS={len(rows)}")

for row in rows:
    print(row)

if len(rows) != 1:
    print("RESULT=FAIL")
else:
    print("RESULT=PASS")

store.close()
