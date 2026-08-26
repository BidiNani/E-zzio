import pytest
import aiosqlite
import json
from dataclasses import asdict
from runtime.agent.contracts import AgentTask, AgentStatus

class TaskRecoveryStore:
    """Gestionnaire de persistance et de reprise de tâches E-ZZIO."""
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS agent_task_checkpoints (
                    task_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    objective TEXT,
                    status TEXT,
                    step_index INTEGER,
                    payload TEXT,
                    updated_at REAL
                );
            """)
            await db.commit()

    async def save_checkpoint(self, task_id: str, session_id: str, objective: str, status: str, step_index: int, payload: dict):
        import time
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO agent_task_checkpoints (task_id, session_id, objective, status, step_index, payload, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    status=excluded.status,
                    step_index=excluded.step_index,
                    payload=excluded.payload,
                    updated_at=excluded.updated_at;
            """, (task_id, session_id, objective, status, step_index, json.dumps(payload), time.time()))
            await db.commit()

    async def load_checkpoint(self, task_id: str) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("""
                SELECT task_id, session_id, objective, status, step_index, payload, updated_at
                FROM agent_task_checkpoints WHERE task_id = ?;
            """, (task_id,))
            row = await cur.fetchone()
            if not row:
                return None
            return {
                "task_id": row[0],
                "session_id": row[1],
                "objective": row[2],
                "status": row[3],
                "step_index": row[4],
                "payload": json.loads(row[5]),
                "updated_at": row[6]
            }

@pytest.mark.asyncio
async def test_task_checkpoint_interruption_and_recovery(tmp_path):
    db_path = str(tmp_path / "task_recovery.db")
    store = TaskRecoveryStore(db_path)
    await store.init()
    
    t_id = "TASK_RECOVERY_TEST_001"
    s_id = "SESS_REC_01"
    obj = "Analyse et traitement de données persistantes"
    
    # 1. Étape 1 : Création et checkpoint initial
    await store.save_checkpoint(t_id, s_id, obj, "EXECUTING", step_index=1, payload={"processed_items": 10})
    
    # 2. Simulation d'un crash / redémarrage du processus
    reloaded_store = TaskRecoveryStore(db_path)
    await reloaded_store.init()
    
    checkpoint = await reloaded_store.load_checkpoint(t_id)
    assert checkpoint is not None
    assert checkpoint["task_id"] == t_id
    assert checkpoint["status"] == "EXECUTING"
    assert checkpoint["step_index"] == 1
    assert checkpoint["payload"]["processed_items"] == 10
    
    # 3. Reprise de la tâche et finalisation idempotente
    await reloaded_store.save_checkpoint(t_id, s_id, obj, "COMPLETED", step_index=2, payload={"processed_items": 20, "final": True})
    
    final_checkpoint = await reloaded_store.load_checkpoint(t_id)
    assert final_checkpoint["status"] == "COMPLETED"
    assert final_checkpoint["step_index"] == 2
    assert final_checkpoint["payload"]["final"] is True
