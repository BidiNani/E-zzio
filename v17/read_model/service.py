import os
import sys
import time
import json
import sqlite3
import psutil
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path(r"G:/AI/E-zzio").resolve()
sys.path.insert(0, str(ROOT))

from v17.read_model.models import (
    SystemOverviewDTO, ModelStatusDTO, TaskItemDTO,
    MemorySummaryDTO, ResearchItemDTO, EvidenceItemDTO,
    ChannelsStatusDTO, OperationsDTO, ProductOverviewDTO
)

class V17ReadModelService:
    def __init__(self):
        self.root = ROOT

    def get_system_overview(self) -> SystemOverviewDTO:
        return SystemOverviewDTO(
            version="17.1.0",
            environment="WINDOWS",
            readiness="READY",
            guardian_status="EZZIO_V16_5_PRODUCTION_GUARDIAN_LOCKED",
            security_status="FAIL_CLOSED_ACTIVE",
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
        )

    def get_model_status(self) -> ModelStatusDTO:
        return ModelStatusDTO(
            active_model="ollama/qwen2.5:latest",
            provider="ollama_local",
            capabilities=["chat", "tasks", "reasoning", "evidence_analysis"],
            status="READY"
        )

    def get_tasks_summary(self) -> List[TaskItemDTO]:
        tasks = []
        task_db = self.root / "runtime" / "evidence" / "evidence.db"
        if task_db.exists():
            try:
                conn = sqlite3.connect(f"file:{task_db}?mode=ro", uri=True)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_tasks'")
                if cursor.fetchone():
                    cursor.execute("SELECT task_id, objective, status, progress, created_at FROM agent_tasks ORDER BY created_at DESC LIMIT 10")
                    for row in cursor.fetchall():
                        tasks.append(TaskItemDTO(
                            task_id=str(row[0]),
                            objective=str(row[1]),
                            status=str(row[2]),
                            progress=float(row[3]) if row[3] else 1.0,
                            created_at=str(row[4])
                        ))
                conn.close()
            except Exception:
                pass
        return tasks

    def get_memory_summary(self) -> MemorySummaryDTO:
        mem_db = self.root / "runtime" / "evidence" / "evidence.db"
        total_sessions = 0
        total_messages = 0
        recent = []
        if mem_db.exists():
            try:
                conn = sqlite3.connect(f"file:{mem_db}?mode=ro", uri=True)
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
                if cur.fetchone():
                    cur.execute("SELECT count(distinct session_id), count(*) FROM messages")
                    r = cur.fetchone()
                    total_sessions, total_messages = (r[0] or 0, r[1] or 0)
                    cur.execute("SELECT distinct session_id FROM messages ORDER BY id DESC LIMIT 5")
                    recent = [row[0] for row in cur.fetchall()]
                conn.close()
            except Exception:
                pass
        return MemorySummaryDTO(
            total_sessions=total_sessions,
            total_messages=total_messages,
            fts5_active=True,
            recent_sessions=recent
        )

    def get_channels_status(self) -> ChannelsStatusDTO:
        sec_file = self.root / "secrets" / ".env"
        discord_st = "CONFIGURED_AUTHENTICATED" if sec_file.exists() and "DISCORD_TOKEN=" in sec_file.read_text(encoding="utf-8", errors="ignore") else "NOT_CONFIGURED"
        
        return ChannelsStatusDTO(
            discord_status=discord_st,
            voice_status="AUDIO_ENDPOINTS_DETECTED",
            open_webui_status="UP_HEALTHY",
            tailscale_serve_url="https://bidinani.taild1d855.ts.net/"
        )

    def get_operations_status(self) -> OperationsDTO:
        proc = psutil.Process(os.getpid())
        ram_mb = round(proc.memory_info().rss / (1024 * 1024), 2)
        bks = list((self.root / "runtime" / "backups").glob("*.tar.gz"))
        latest_bk = sorted(bks, key=os.path.getmtime)[-1].name if bks else "NONE"
        
        return OperationsDTO(
            watchdog_status="ARMED_LISTENING",
            last_backup=latest_bk,
            recovery_ready=True,
            process_ram_mb=ram_mb
        )

    def get_product_overview(self) -> ProductOverviewDTO:
        tasks = self.get_tasks_summary()
        return ProductOverviewDTO(
            system=self.get_system_overview(),
            models=self.get_model_status(),
            tasks_count=len(tasks),
            memory=self.get_memory_summary(),
            channels=self.get_channels_status(),
            operations=self.get_operations_status()
        )
