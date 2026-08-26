import pytest
import aiosqlite
import json
import time

class PersistentTaskManager:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS persistent_tasks (
                    task_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    objective TEXT,
                    status TEXT,
                    step_index INTEGER,
                    result TEXT,
                    updated_at REAL
                );
            """)
            await db.commit()

    async def save_task(self, task_id: str, session_id: str, objective: str, status: str, step_index: int, result: dict = None):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO persistent_tasks (task_id, session_id, objective, status, step_index, result, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    status=excluded.status,
                    step_index=excluded.step_index,
                    result=excluded.result,
                    updated_at=excluded.updated_at;
            """, (task_id, session_id, objective, status, step_index, json.dumps(result or {}), time.time()))
            await db.commit()

    async def get_task(self, task_id: str):
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("SELECT task_id, session_id, objective, status, step_index, result FROM persistent_tasks WHERE task_id = ?;", (task_id,))
            row = await cur.fetchone()
            if not row:
                return None
            return {
                "task_id": row[0],
                "session_id": row[1],
                "objective": row[2],
                "status": row[3],
                "step_index": row[4],
                "result": json.loads(row[5])
            }

@pytest.mark.asyncio
async def test_phase7_task_persistence_restart_and_resume(tmp_path):
    db_file = str(tmp_path / "task_persistence_p7.db")
    mgr1 = PersistentTaskManager(db_file)
    await mgr1.init()
    
    t_id = "TASK_P7_PERSIST_001"
    # Étape 1 : Création et interruption
    await mgr1.save_task(t_id, "SESS_P7", "Objectif lourd", "EXECUTING", step_index=1, result={"step_1": "DONE"})
    
    # Étape 2 : Simulation crash et redémarrage avec un nouveau manager
    mgr2 = PersistentTaskManager(db_file)
    await mgr2.init()
    
    t_recovered = await mgr2.get_task(t_id)
    assert t_recovered is not None
    assert t_recovered["status"] == "EXECUTING"
    assert t_recovered["step_index"] == 1
    
    # Étape 3 : Reprise et complétion
    await mgr2.save_task(t_id, "SESS_P7", "Objectif lourd", "COMPLETED", step_index=2, result={"step_1": "DONE", "step_2": "DONE", "verified": True})
    
    t_final = await mgr2.get_task(t_id)
    assert t_final["status"] == "COMPLETED"
    assert t_final["step_index"] == 2
    assert t_final["result"]["verified"] is True
