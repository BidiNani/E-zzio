"""
E-ZZIO V7.59.1 — Cognitive Query Engine (Hippocampus with BM25 Floor)
Intègre un plancher sémantique pour protéger les souvenirs critiques (Importance 10/10)
d'un mauvais score lexical brut.
"""
import sqlite3
import json
import math
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(r"G:\AI\E-zzio")
INDEX_DB = ROOT_DIR / "runtime" / "cognitive" / "index" / "memory_index.sqlite"

PROVENANCE_TRUST = {
    "identity_core": 1.00,
    "IDENTITY": 1.00,
    "RPG_MEMORY": 0.95,
    "experience_ledger": 0.85,
    "EXPERIENCE": 0.85,
    "security_audit": 0.50,
    "SECURITY": 0.50,
    "OPERATIONAL": 0.30,
    "generic": 0.20
}

class CognitiveHippocampus:
    def __init__(self):
        self.db_path = INDEX_DB

    def _calculate_temporal_decay(self, last_validated_iso: str) -> float:
        try:
            dt = datetime.fromisoformat(last_validated_iso.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            days_old = (now - dt).days
            decay = math.exp(-0.693 * (days_old / 180.0))
            return max(0.5, decay)
        except Exception:
            return 1.0

    def query(self, search_term: str, limit: int = 10, min_score: float = 0.05) -> list:
        if not self.db_path.exists():
            return []

        uri = f"file:{self.db_path}?mode=ro"
        results = []

        with sqlite3.connect(uri, uri=True) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT content, memory_type, source_path, confidence, importance, last_validated, rank
                FROM memory_search
                WHERE memory_search MATCH ?
                ORDER BY rank
                LIMIT 50;
            """, (search_term,))
            
            rows = cursor.fetchall()

            for content, memory_type, source_path, confidence, importance, last_validated, bm25_rank in rows:
                trust = PROVENANCE_TRUST.get(memory_type, 0.30)
                decay = self._calculate_temporal_decay(last_validated)
                
                # Correction V7.59.1 : Plancher sémantique à 0.25 pour ne pas écraser les fondamentaux
                semantic_weight = max(0.25, 1.0 / (1.0 + abs(bm25_rank)))
                
                cognitive_score = (importance / 10.0) * confidence * trust * decay
                final_score = cognitive_score * semantic_weight

                if final_score >= min_score:
                    results.append({
                        "content": content[:200],
                        "memory_type": memory_type,
                        "source_path": source_path,
                        "cognitive_score": round(final_score, 4),
                        "importance": importance,
                        "confidence": confidence,
                        "trust_multiplier": trust
                    })

        results.sort(key=lambda x: x["cognitive_score"], reverse=True)
        return results[:limit]

if __name__ == "__main__":
    hippocampus = CognitiveHippocampus()
    print("\n[V7.59.1] Moteur mis à jour avec plancher BM25.")
