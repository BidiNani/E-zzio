"""Tests unitaires déterministes pour la capacité DATA (DataSourceManager) dans l'orchestration de missions EzzioMaster."""

import pytest
import asyncio
import sqlite3
import tempfile
import time
from pathlib import Path
from core.ezzio_master import EzzioMaster
from core.providers.base_provider import CostClass, ProviderResponse


class FakeDataMissionProvider:
    """Provider fake déterministe enregistrant les prompts pour valider l'injection d'actions SQL réelles."""

    def __init__(self):
        self.calls = []

    async def generate(
        self,
        prompt: str = "",
        system_prompt: str = None,
        model: str = "gemini-3.8-flash",
        temperature: float = 0.2,
        max_tokens: int = 512,
        thinking_level: str = "off",
        **kwargs
    ) -> ProviderResponse:
        self.calls.append({
            "prompt": prompt,
            "system_prompt": system_prompt,
            "model": model,
            "thinking_level": thinking_level,
        })
        return ProviderResponse(
            content=f"[Fake LLM Data Response for: {prompt[:40]}]",
            model=model,
            provider="fake_data_mission_provider",
            cost_class=CostClass.LOCAL,
        )


@pytest.mark.asyncio
async def test_mission_with_real_sql_data_execution():
    """1. Mission avec exécution réelle de requête SQL paramétrée sur base SQLite temporaire."""
    fake_prov = FakeDataMissionProvider()
    master = EzzioMaster(provider=fake_prov)

    # Création d'une base SQLite temporaire réelle
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".db", dir="G:/AI/E-zzio/runtime") as tmp:
        db_path = tmp.name

    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE security_audits (id INT, severity TEXT, summary TEXT);")
    conn.execute("INSERT INTO security_audits VALUES (1, 'HIGH', 'SQL Injection vulnerability detected in legacy api');")
    conn.execute("INSERT INTO security_audits VALUES (2, 'CRITICAL', 'Hardcoded API secret in configuration file');")
    conn.commit()
    conn.close()

    try:
        subtasks = [
            {
                "task_id": "subtask-sql-query-01",
                "role": "DATA_ANALYSIS",
                "prompt": "Extraire et analyser les audits de sécurité de sévérité CRITICAL",
                "db_path": db_path,
                "sql_query": "SELECT * FROM security_audits WHERE severity = ?;",
                "params": ("CRITICAL",),
                "complexity": 0.6
            }
        ]

        res = await master.orchestrate_multi_agent_mission(
            mission_prompt="Auditer la base de sécurité locale",
            subtask_specs=subtasks
        )

        assert res["ok"] is True
        assert len(res["subtasks"]) == 1
        st = res["subtasks"][0]

        # Vérification de l'exécution d'action réelle SQL
        assert st["preflight_ready"] is True
        assert st["action_executed"] is True
        assert st["action_status"] == "READY"
        assert st["action_valid"] is True

        # Le prompt reçu par le provider de la sous-tâche DOIT contenir le résultat SQL réel
        subtask_call = fake_prov.calls[0]
        assert "Hardcoded API secret in configuration file" in subtask_call["prompt"]
        assert "CRITICAL" in subtask_call["prompt"]

        # Synthèse Master
        assert res["synthesis"] is not None
        assert len(fake_prov.calls) == 2  # 1 subtask + 1 synthesis master

    finally:
        Path(db_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_sql_data_execution_controlled_failure_bad_query():
    """2. Échec contrôlé d'une requête SQL invalide (syntaxe SQL incorrecte)."""
    fake_prov = FakeDataMissionProvider()
    master = EzzioMaster(provider=fake_prov)

    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".db", dir="G:/AI/E-zzio/runtime") as tmp:
        db_path = tmp.name

    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE dummy (id INT);")
    conn.commit()
    conn.close()

    try:
        subtasks = [
            {
                "task_id": "subtask-bad-sql-01",
                "role": "DATA_ANALYSIS",
                "prompt": "Exécuter une requête invalide",
                "db_path": db_path,
                "sql_query": "SELECT * FROM non_existent_table_9999;",
                "complexity": 0.5
            }
        ]

        res = await master.orchestrate_multi_agent_mission(
            mission_prompt="Test d'erreur SQL contrôlée",
            subtask_specs=subtasks
        )

        assert res["ok"] is True
        st = res["subtasks"][0]
        assert st["action_executed"] is True
        assert st["action_status"] == "ERROR"
        assert st["action_valid"] is False

    finally:
        Path(db_path).unlink(missing_ok=True)
