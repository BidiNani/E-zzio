from runtime.memory.session import WorkingMemory

print("[START] WorkingMemory test")

m = WorkingMemory(db_path=":memory:")

print(f"SESSION={m.session_id}")

m.add(
    "user",
    "FORENSIC_WORKING_MEMORY_TEST",
    source="validation"
)

print("\n[RECENT]")
rows = m.recent(5)

print(f"ROWS={len(rows)}")

for row in rows:
    print(row)

if (
    len(rows) == 1
    and rows[0]["role"] == "user"
    and rows[0]["content"] == "FORENSIC_WORKING_MEMORY_TEST"
):
    print("RESULT=PASS")
else:
    print("RESULT=FAIL")

m.close()
