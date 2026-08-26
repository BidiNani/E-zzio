import sqlite3
import json
import math


class VectorStore:
    def __init__(self, db_path="runtime/memory/semantic/memory.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("CREATE TABLE IF NOT EXISTS memory (id TEXT PRIMARY KEY, vector TEXT, content TEXT)")
        self.conn.commit()

    def add(self, memory_id, vector, content):
        self.conn.execute("INSERT OR REPLACE INTO memory VALUES (?, ?, ?)", (memory_id, json.dumps(vector), content))
        self.conn.commit()

    def _cosine_similarity(self, v1, v2):
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def search(self, query_vector, top_k=3):
        cursor = self.conn.execute("SELECT id, vector, content FROM memory")
        rows = cursor.fetchall()
        scored = []
        for row in rows:
            vec = json.loads(row[1])
            score = self._cosine_similarity(query_vector, vec)
            scored.append((score, row[2]))

        # Tri par score de similarité décroissant
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k]]
