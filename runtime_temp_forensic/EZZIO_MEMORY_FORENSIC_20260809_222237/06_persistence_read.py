from runtime.memory.session import WorkingMemory

m = WorkingMemory(
    db_path=r"C:\Users\enrik\AppData\Local\Temp\EZZIO_MEMORY_FORENSIC_20260809_222237\persistence_test.db"
)

print("SESSION=" + m.session_id)
print("READ_RECENT=" + repr(m.recent(10)))

m.close()
