from pathlib import Path

print("[*] Reconstruction propre OutputGuard + ActionStore")

# ============================================================
# OUTPUT GUARD STABLE
# ============================================================

guard = r'''
class OutputGuard:

    def __init__(self, max_size=65536):
        self.max_size = max_size
        self._buffer = []
        self._error_buffer = []
        self.truncated = False


    def feed(self, data):
        if data is None:
            return

        text = str(data)

        current = len(self.get_output())

        if current + len(text) > self.max_size:
            remaining = self.max_size - current

            if remaining > 0:
                self._buffer.append(text[:remaining])

            self.truncated = True
        else:
            self._buffer.append(text)


    def feed_error(self, data):
        if data:
            self._error_buffer.append(str(data))


    def get_output(self):
        return "".join(self._buffer)


    def get_error(self):
        return "".join(self._error_buffer)


    def is_success(self):
        return True


    def clear(self):
        self._buffer.clear()
        self._error_buffer.clear()
        self.truncated=False
'''

Path("runtime/external/output_guard.py").write_text(
    guard,
    encoding="utf-8"
)

print("[+] OutputGuard reconstruit")


# ============================================================
# ACTION STORE
# ============================================================

store = Path("runtime/action/store.py")

if store.exists():

    code = store.read_text(encoding="utf-8")

    old = "ORDER BY timestamp DESC"

    code = code.replace(
        old,
        "ORDER BY timestamp DESC, rowid DESC"
    )

    store.write_text(
        code,
        encoding="utf-8"
    )

    print("[+] ActionStore stabilisé")

print("[OK] Reconstruction terminée")
