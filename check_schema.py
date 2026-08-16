import sqlite3
c = sqlite3.connect("runtime/evidence/evidence.db")
result = c.execute("SELECT sql FROM sqlite_master WHERE name='evidence'").fetchone()
print(result)
