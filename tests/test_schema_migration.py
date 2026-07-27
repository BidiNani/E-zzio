import sqlite3
import pytest
from runtime.action.store import ActionStore

def test_old_database_migrates_transition_hash(tmp_path):
    """Vérifie qu'une ancienne base de données sans transition_hash est mise à niveau automatiquement."""
    db = tmp_path / "old.db"
    
    # 1. Simulation d'une base ancienne version (sans la colonne transition_hash)
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE state_transitions(
            transition_id TEXT PRIMARY KEY,
            exec_id TEXT,
            from_state TEXT,
            to_state TEXT,
            timestamp TEXT
        )
    """)
    # Insertion d'une ancienne transition orpheline sans hash
    conn.execute(
        "INSERT INTO state_transitions VALUES (?, ?, ?, ?, ?)",
        ("tx_old_123", "exec_legacy", "CREATED", "VALIDATING", "2026-01-01T00:00:00Z")
    )
    conn.commit()
    conn.close()

    # 2. Instanciation du Store déclenchant la migration et la réparation automatique
    store = ActionStore(str(db))

    # 3. Vérification forensic post-migration
    conn = sqlite3.connect(db)
    cols = {x[1] for x in conn.execute("PRAGMA table_info(state_transitions)").fetchall()}
    assert "transition_hash" in cols, "La colonne transition_hash n'a pas été ajoutée par la migration !"

    # Vérification que l'ancienne ligne a bien été réparée (hash généré)
    cursor = conn.execute("SELECT transition_hash FROM state_transitions WHERE transition_id = 'tx_old_123'")
    row = cursor.fetchone()
    assert row is not None
    assert len(row[0]) == 64, "Le hash SHA256 de réparation est invalide !"
    conn.close()
