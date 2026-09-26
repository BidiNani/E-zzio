"""
core/agent/mission_controller.py — Mission Controller & Task Management Gateways
"""
from __future__ import annotations

import enum
import json
import sqlite3
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class MissionStatus(enum.StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PAUSED = "PAUSED"
    UNKNOWN = "UNKNOWN"


class TaskStatus(enum.StrEnum):
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PAUSING = "PAUSING"
    PAUSED = "PAUSED"
    RESUMING = "RESUMING"
    CANCELLING = "CANCELLING"
    CANCELLED = "CANCELLED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class WorkerRole(enum.StrEnum):
    CODER = "CODER"
    RESEARCHER = "RESEARCHER"
    QA = "QA"
    SECURITY = "SECURITY"
    MASTER = "MASTER"


@dataclass
class MissionRecord:
    mission_id: str
    goal: str
    worker_type: str = "CODER_WORKER"
    status: MissionStatus = MissionStatus.QUEUED
    request_id: str = ""
    model: str = ""
    provider: str = ""
    result: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    _async_task: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.mission_id,
            "mission_id": self.mission_id,
            "title": self.goal,
            "name": self.goal,
            "description": self.goal,
            "worker_type": self.worker_type,
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
            "request_id": self.request_id,
            "model": self.model,
            "provider": self.provider,
            "result": self.result,
            "created_at": self.created_at,
            "createdAt": self.created_at,
            "tasks": [],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MissionRecord:
        status_raw = data.get("status", "QUEUED")
        try:
            status = MissionStatus(status_raw)
        except ValueError:
            status = MissionStatus.UNKNOWN
        return cls(
            mission_id=data.get("mission_id") or data.get("id") or "",
            goal=data.get("goal") or data.get("title") or "",
            worker_type=data.get("worker_type", "CODER_WORKER"),
            status=status,
            request_id=data.get("request_id", ""),
            model=data.get("model", ""),
            provider=data.get("provider", ""),
            result=data.get("result") or {},
            created_at=data.get("created_at") or data.get("createdAt") or "",
        )


@dataclass
class MissionTask:
    task_id: str
    title: str
    description: str
    role: WorkerRole = WorkerRole.CODER
    status: TaskStatus = TaskStatus.CREATED

    def transition_to(self, new_status: TaskStatus | str) -> bool:
        if isinstance(new_status, str):
            try:
                new_status = TaskStatus(new_status)
            except ValueError:
                return False
        self.status = new_status
        return True


@dataclass
class TaskGraph:
    nodes: dict[str, MissionTask] = field(default_factory=dict)


class MissionRegistry:
    def __init__(self, db_path: str | Path | None = None):
        self._missions: dict[str, MissionRecord] = {}
        self._dag_checkpoints: dict[str, dict[str, Any]] = {}
        if db_path is None:
            self.db_path = Path("runtime/missions/missions.db").resolve()
        elif isinstance(db_path, str):
            self.db_path = Path(db_path).resolve()
        else:
            self.db_path = db_path.resolve()
        self._write_lock = threading.Lock()
        self._init_db()
        self._load_from_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._write_lock:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS mission_records (
                        mission_id TEXT PRIMARY KEY,
                        goal TEXT NOT NULL,
                        worker_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        request_id TEXT,
                        model TEXT,
                        provider TEXT,
                        result_json TEXT NOT NULL,
                        created_at TEXT,
                        dag_json TEXT
                    );
                """)
                conn.commit()

    def _load_from_db(self) -> None:
        try:
            with self._get_connection() as conn:
                rows = conn.execute("SELECT * FROM mission_records").fetchall()
                for row in rows:
                    rec_dict = {
                        "mission_id": row["mission_id"],
                        "goal": row["goal"],
                        "worker_type": row["worker_type"],
                        "status": row["status"],
                        "request_id": row["request_id"] or "",
                        "model": row["model"] or "",
                        "provider": row["provider"] or "",
                        "result": json.loads(row["result_json"]) if row["result_json"] else {},
                        "created_at": row["created_at"] or "",
                    }
                    record = MissionRecord.from_dict(rec_dict)
                    self._missions[record.mission_id] = record
                    if row["dag_json"]:
                        try:
                            self._dag_checkpoints[record.mission_id] = json.loads(row["dag_json"])
                        except Exception:
                            pass
        except Exception:
            pass

    def _save_record_to_db(self, record: MissionRecord, dag: Any = None) -> None:
        dag_json_str = None
        if dag is not None:
            if hasattr(dag, "to_dict"):
                dag_json_str = json.dumps(dag.to_dict())
            elif isinstance(dag, dict):
                dag_json_str = json.dumps(dag)
        elif record.mission_id in self._dag_checkpoints:
            dag_json_str = json.dumps(self._dag_checkpoints[record.mission_id])

        with self._write_lock:
            try:
                with self._get_connection() as conn:
                    conn.execute("""
                        INSERT INTO mission_records (
                            mission_id, goal, worker_type, status, request_id, model, provider, result_json, created_at, dag_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(mission_id) DO UPDATE SET
                            goal = excluded.goal,
                            worker_type = excluded.worker_type,
                            status = excluded.status,
                            request_id = excluded.request_id,
                            model = excluded.model,
                            provider = excluded.provider,
                            result_json = excluded.result_json,
                            created_at = excluded.created_at,
                            dag_json = COALESCE(excluded.dag_json, mission_records.dag_json);
                    """, (
                        record.mission_id,
                        record.goal,
                        record.worker_type,
                        record.status.value if hasattr(record.status, "value") else str(record.status),
                        record.request_id,
                        record.model,
                        record.provider,
                        json.dumps(record.result or {}),
                        record.created_at,
                        dag_json_str,
                    ))
                    conn.commit()
            except Exception:
                pass

    def register(self, record: MissionRecord, dag: Any = None) -> None:
        self._missions[record.mission_id] = record
        self._save_record_to_db(record, dag)

    def update_mission(self, record: MissionRecord, dag: Any = None) -> None:
        self._missions[record.mission_id] = record
        self._save_record_to_db(record, dag)

    def checkpoint_dag(self, mission_id: str, dag: Any) -> None:
        m = self._missions.get(mission_id)
        dag_dict = dag.to_dict() if hasattr(dag, "to_dict") else dag
        self._dag_checkpoints[mission_id] = dag_dict
        if m:
            self._save_record_to_db(m, dag)

    def get_dag_checkpoint(self, mission_id: str) -> dict[str, Any] | None:
        return self._dag_checkpoints.get(mission_id)

    def get(self, mission_id: str) -> MissionRecord | None:
        return self._missions.get(mission_id)

    def list_all(self) -> list[MissionRecord]:
        return list(self._missions.values())

    def cancel(self, mission_id: str) -> bool:
        m = self._missions.get(mission_id)
        if not m:
            return False
        m.status = MissionStatus.CANCELLED
        self._save_record_to_db(m)
        task = getattr(m, "_async_task", None)
        if task and not task.done():
            task.cancel()
        return True

    def pause(self, mission_id: str) -> bool:
        m = self._missions.get(mission_id)
        if not m:
            return False
        m.status = MissionStatus.PAUSED
        self._save_record_to_db(m)
        return True

    def resume(self, mission_id: str) -> bool:
        m = self._missions.get(mission_id)
        if not m:
            return False
        m.status = MissionStatus.RUNNING
        self._save_record_to_db(m)
        return True

    def get_active_mission_for_session(self, session_id: str) -> MissionRecord | None:
        if not session_id:
            return None
        for m in reversed(list(self._missions.values())):
            if m.request_id == session_id and m.status in (MissionStatus.RUNNING, MissionStatus.PAUSED, MissionStatus.QUEUED):
                return m
        return None

    def get_latest_mission_for_session(self, session_id: str) -> MissionRecord | None:
        if not session_id:
            return None
        for m in reversed(list(self._missions.values())):
            if m.request_id == session_id:
                return m
        return None


mission_registry = MissionRegistry()


class MissionController:
    def __init__(self, *args, **kwargs):
        pass


mission_controller = MissionController()
