import sqlite3
import json

class VectorStore:
    def __init__(self, db_path="runtime/agent/ledger/memory.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("CREATE TABLE IF NOT EXISTS memory (id TEXT PRIMARY KEY, vector TEXT, content TEXT)")
        self.conn.commit()

    def add(self, memory_id, vector, content):
        self.conn.execute("INSERT OR REPLACE INTO memory VALUES (?, ?, ?)", 
                          (memory_id, json.dumps(vector), content))
        self.conn.commit()

    def search(self, vector):
        # Simplification : retourne tout pour valider l'intégration avant calcul cosinus
        cursor = self.conn.execute("SELECT content FROM memory LIMIT 5")
        return [row[0] for row in cursor.fetchall()]