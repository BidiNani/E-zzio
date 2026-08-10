imports = [
    "runtime.memory",
    "runtime.memory.session",
    "runtime.memory.events",
    "runtime.memory.sqlite.store",
    "runtime.core.message"
]

for name in imports:
    try:
        __import__(name)
        print(f"PASS|{name}")
    except Exception as e:
        print(f"FAIL|{name}|{type(e).__name__}: {e}")
