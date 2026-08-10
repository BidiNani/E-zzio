# ==============================================================================
# E-ZZIO SOVEREIGN MEMORY CORE (V1 - INTERACTIONS LEDGER)
# ==============================================================================
import sqlite3
import pathlib
from datetime import datetime

class MemoryCore:
    """
    Le lobe frontal d'E-zzio. 
    Gère la persistance conversationnelle via la table 'interactions' (memory.sqlite3).
    """
    def __init__(self):
        self.db_path = pathlib.Path(r"G:\AI\E-zzio\runtime\memory\database\memory.sqlite3")
        self._verify_connection()

    def _verify_connection(self):
        if not self.db_path.exists():
            print(f"[!] Attention : Base de données introuvable à {self.db_path}")

    def injecter_interaction(self, user_id: str, role: str, message: str):
        action_type = "user_message" if role == "user" else "assistant_response"
        timestamp = datetime.utcnow().isoformat()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO interactions (timestamp, user_id, action, details, sentiment)
                    VALUES (?, ?, ?, ?, ?)
                """, (timestamp, user_id, action_type, message, "neutral"))
                conn.commit()
        except Exception as e:
            print(f"[X] Erreur lors de l'ancrage de la mémoire : {e}")

    def extraire_contexte_recent(self, user_id: str, limite: int = 10) -> list:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT action, details FROM (
                        SELECT action, details, id 
                        FROM interactions 
                        WHERE user_id = ? AND action IN ('user_message', 'assistant_response')
                        ORDER BY id DESC 
                        LIMIT ?
                    ) ORDER BY id ASC
                """, (user_id, limite))
                lignes = cursor.fetchall()

            contexte = []
            for action, details in lignes:
                role = "user" if action == "user_message" else "model"
                contexte.append({"role": role, "text": details})
            
            return contexte
        
        except Exception as e:
            print(f"[X] Erreur lors de l'extraction de la mémoire : {e}")
            return []
