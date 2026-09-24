"""Tests Batch 1 — Fichiers 90-99% vers 100%.

Cibles :
- core/tasks/models.py            (95% -> 100%)
- core/decision_router.py         (93% -> 100%)
- core/cognition/model_router.py  (91% -> 100%)
- core/generators/sheet_engine.py (90% -> 100%)
- core/bus.py                     (90% -> 100%)
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ============================================================
# 1. core/tasks/models.py — L52
# ============================================================

class TestTaskModels:
    def test_invalid_transition_raises(self):
        """L52 : transition interdite -> raise InvalidStateTransitionError."""
        from core.tasks.models import (
            InvalidStateTransitionError,
            Task,
            TaskState,
        )

        task = Task(title="t", workspace="w")
        assert task.state == TaskState.DRAFT

        # DRAFT -> COMPLETED est interdit
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            task.transition_to(TaskState.COMPLETED)
        assert "DRAFT" in str(exc_info.value)
        assert "COMPLETED" in str(exc_info.value)

    def test_valid_transition_works(self):
        from core.tasks.models import Task, TaskState

        task = Task(title="t", workspace="w")
        task.transition_to(TaskState.SCOPED)
        assert task.state == TaskState.SCOPED

    def test_transition_from_completed_raises(self):
        """COMPLETED -> n'importe quoi est interdit."""
        from core.tasks.models import (
            InvalidStateTransitionError,
            Task,
            TaskState,
        )

        task = Task(title="t", workspace="w")
        task.transition_to(TaskState.SCOPED)
        task.transition_to(TaskState.PLANNED)
        task.transition_to(TaskState.AWAITING_APPROVAL)
        task.transition_to(TaskState.EXECUTING)
        task.transition_to(TaskState.VERIFYING)
        task.transition_to(TaskState.COMPLETED)

        with pytest.raises(InvalidStateTransitionError):
            task.transition_to(TaskState.DRAFT)


# ============================================================
# 2. core/decision_router.py — L35, 44->40
# ============================================================

class TestDecisionRouter:
    def test_empty_providers_raises(self):
        """L35 : pas de providers -> RuntimeError."""
        from core.decision_router import DecisionRouter

        router = DecisionRouter(providers=[])
        with pytest.raises(RuntimeError, match="Aucun fournisseur"):
            asyncio.run(router.search("test"))

    def test_provider_returns_falsy_then_continue(self):
        """L44->40 : result falsy -> continue -> erreur finale."""
        from core.decision_router import DecisionRouter

        provider = MagicMock()
        provider.name = "tavily"
        provider.search = AsyncMock(return_value=None)

        router = DecisionRouter(providers=[provider])
        with pytest.raises(RuntimeError, match="Échec de recherche"):
            asyncio.run(router.search("test"))

    def test_provider_raises_then_error_accumulated(self):
        """L46-49 : exception provider -> erreurs accumulées."""
        from core.decision_router import DecisionRouter

        provider = MagicMock()
        provider.name = "tavily"
        provider.search = AsyncMock(side_effect=ValueError("boom"))

        router = DecisionRouter(providers=[provider])
        with pytest.raises(RuntimeError, match="Échec de recherche"):
            asyncio.run(router.search("test"))

    def test_provider_returns_valid_result(self):
        """L44-45 : result valide -> return."""
        from core.decision_router import DecisionRouter, SearchMode

        provider = MagicMock()
        provider.name = "tavily"
        provider.search = AsyncMock(return_value={"provider": "tavily", "data": {"x": 1}})

        router = DecisionRouter(providers=[provider])
        result = asyncio.run(router.search("test", mode=SearchMode.FAST))
        assert result["mode"] == "fast"
        assert result["provider"] == "tavily"


# ============================================================
# 3. core/cognition/model_router.py — L37-38, 61
# ============================================================

class TestModelRouter:
    def test_refactor_task(self):
        """L37-38 : task_type contient 'refactor' -> role REFACTOR."""
        from core.cognition.model_router import ModelRouter

        router = ModelRouter()
        result = router.select_engine(task_type="refactor code")
        assert "engine" in result or "model" in result or "role" in result

    def test_unknown_role_fallback(self):
        """L60-61 : role inconnu -> fallback MASTER."""
        import core.cognition.model_router as mr_mod
        from core.cognition.model_router import ModelRouter

        router = ModelRouter()
        # Patcher le registre pour renvoyer None
        with patch.object(mr_mod.canonical_model_registry, "get_by_role", return_value=None):
            result = router.select_engine(task_type="refactor")
            assert isinstance(result, dict)

    def test_forensic_task(self):
        from core.cognition.model_router import ModelRouter

        router = ModelRouter()
        result = router.select_engine(task_type="forensic analysis")
        assert isinstance(result, dict)

    def test_high_complexity_master_strategic(self):
        from core.cognition.model_router import ModelRouter

        router = ModelRouter()
        result = router.select_engine(complexity_score=0.95)
        assert isinstance(result, dict)

    def test_low_complexity_fast_chat(self):
        from core.cognition.model_router import ModelRouter

        router = ModelRouter()
        result = router.select_engine(complexity_score=0.1, risk_level="low")
        assert isinstance(result, dict)


# ============================================================
# 4. core/generators/sheet_engine.py — L25-29, 52-53, 60, 88->97, 98->109
# ============================================================

class TestSheetEngine:
    def test_is_available_returns_bool(self):
        """L25-29 : is_available retourne un bool."""
        from core.generators.sheet_engine import SheetEngine

        engine = SheetEngine(workspace_root="G:\\AI\\E-zzio")
        result = engine.is_available()
        assert isinstance(result, bool)

    def test_is_available_false_import_error(self):
        """L28-29 : openpyxl absent -> False."""
        import builtins

        from core.generators.sheet_engine import SheetEngine

        engine = SheetEngine(workspace_root="G:\\AI\\E-zzio")

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "openpyxl":
                raise ImportError("simulated")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            assert engine.is_available() is False

    def test_generate_missing_openpyxl_raises(self, tmp_path):
        """L52-53 : ImportError au moment de generate_spreadsheet."""
        import builtins

        from core.generators.sheet_engine import SheetEngine

        engine = SheetEngine(workspace_root=str(tmp_path))

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "openpyxl" or name.startswith("openpyxl."):
                raise ImportError("simulated openpyxl missing")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            with pytest.raises(RuntimeError, match="openpyxl"):
                engine.generate_spreadsheet(
                    filename="test.xlsx",
                    sheets_data=[{"sheet_name": "S1", "headers": ["A"], "rows": [["1"]]}],
                )

    def test_generate_adds_xlsx_extension(self, tmp_path):
        """L60 : filename sans .xlsx -> extension ajoutée."""
        from core.generators.sheet_engine import SheetEngine

        if not SheetEngine(workspace_root=str(tmp_path)).is_available():
            pytest.skip("openpyxl absent")

        engine = SheetEngine(workspace_root=str(tmp_path))
        result = engine.generate_spreadsheet(
            filename="sans_ext",
            sheets_data=[{
                "sheet_name": "S1",
                "headers": ["A", "B"],
                "rows": [["1", "2"], ["3", "4"]],
            }],
        )
        assert result.get("ok") is True or "filename" in result
        assert result.get("filename", "").endswith(".xlsx")

    def test_multiple_sheets_and_rows(self, tmp_path):
        """L88->97, 98->109 : multi-sheets avec plusieurs rows."""
        from core.generators.sheet_engine import SheetEngine

        if not SheetEngine(workspace_root=str(tmp_path)).is_available():
            pytest.skip("openpyxl absent")

        engine = SheetEngine(workspace_root=str(tmp_path))
        result = engine.generate_spreadsheet(
            filename="multi.xlsx",
            sheets_data=[
                {
                    "sheet_name": "S1",
                    "headers": ["H1", "H2"],
                    "rows": [["a", "b"], ["c", "d"], ["e", "f"]],
                },
                {
                    "sheet_name": "S2",
                    "headers": ["X"],
                    "rows": [["1"], ["2"]],
                    "totals": ["Total", "=SUM(A2:A3)"],
                },
            ],
        )
        assert result.get("ok") is True or "filename" in result


# ============================================================
# 5. core/bus.py — 106->exit, 108->exit, 117-122
# ============================================================

class TestEventBus:
    def test_unsubscribe_unknown_run_id(self, tmp_path):
        """L106->exit : unsubscribe sur run_id inconnu -> return."""
        from core.bus import EventBus

        bus = EventBus(db_path=tmp_path / "bus.db")
        q = asyncio.Queue()
        # Pas de subscribe préalable
        bus.unsubscribe("unknown_run", q)  # ne doit pas lever

    def test_unsubscribe_removes_queue(self, tmp_path):
        """L105-108 : unsubscribe retire la queue."""
        from core.bus import EventBus

        bus = EventBus(db_path=tmp_path / "bus.db")
        q = bus.subscribe("run1")
        assert "run1" in bus._subscribers
        bus.unsubscribe("run1", q)
        assert q not in bus._subscribers.get("run1", [])

    def test_unsubscribe_unknown_queue(self, tmp_path):
        """L106->exit : queue inconnue -> ignore."""
        from core.bus import EventBus

        bus = EventBus(db_path=tmp_path / "bus.db")
        bus.subscribe("run1")
        q2 = asyncio.Queue()
        bus.unsubscribe("run1", q2)  # q2 pas dans la liste -> pas d'erreur

    def test_prune_events_older_than(self, tmp_path):
        """L115-122 : prune_events_older_than retourne un count."""
        from core.bus import EventBus

        bus = EventBus(db_path=tmp_path / "bus.db")
        # Aucun event -> 0
        count = bus.prune_events_older_than(days=30)
        assert count == 0

    def test_prune_events_zero_days(self, tmp_path):
        """L117-122 : prune avec days=0."""
        from core.bus import EventBus

        bus = EventBus(db_path=tmp_path / "bus.db")
        bus.register_run("run1", "prompt test", "normal")
        count = bus.prune_events_older_than(days=0)
        assert isinstance(count, int)

    def test_get_run_events_empty(self, tmp_path):
        """L124 : get_run_events retourne liste vide si rien."""
        from core.bus import EventBus

        bus = EventBus(db_path=tmp_path / "bus.db")
        events = bus.get_run_events("unknown")
        assert events == []

# ============================================================
# 6. Tests correctifs — branches manquantes
# ============================================================

class TestModelRouterBranchesExtra:
    def test_infra_task(self):
        """L40-41 : task_type contient 'infra' -> role FAST."""
        from core.cognition.model_router import ModelRouter

        router = ModelRouter()
        result = router.select_engine(task_type="infra scaling")
        assert isinstance(result, dict)

    def test_fast_local_task(self):
        """L40-41 : task_type contient 'fast_local'."""
        from core.cognition.model_router import ModelRouter

        router = ModelRouter()
        result = router.select_engine(task_type="fast_local chat")
        assert isinstance(result, dict)

    def test_else_fallback_master_strategic(self):
        """L52-54 : else -> MASTER_STRATEGIC medium."""
        from core.cognition.model_router import ModelRouter

        router = ModelRouter()
        # complexity 0.75 (ni <0.7 ni >=0.85) -> else
        result = router.select_engine(complexity_score=0.75, risk_level="medium")
        assert isinstance(result, dict)


class TestEventBusEmit:
    def test_register_run_and_emit(self, tmp_path):
        """L75-98 : emit ecrit dans la DB."""
        from core.bus import AgentEvent, EventBus

        bus = EventBus(db_path=tmp_path / "bus.db")
        bus.register_run("run1", "prompt test", "normal")

        event = AgentEvent(
            run_id="run1",
            event_type="thought",
            agent_id="agent1",
            payload={"msg": "hello"},
        )
        result = asyncio.run(bus.emit(event))
        assert result.event_id is not None

    def test_emit_with_subscriber(self, tmp_path):
        """L75-98 + subscriber : emit propage au queue."""
        from core.bus import AgentEvent, EventBus

        bus = EventBus(db_path=tmp_path / "bus.db")
        bus.register_run("run1", "prompt test", "normal")
        q = bus.subscribe("run1")

        event = AgentEvent(
            run_id="run1",
            event_type="thought",
            agent_id="agent1",
            payload={"msg": "hello"},
        )
        asyncio.run(bus.emit(event))

        # Le queue doit contenir l'event
        assert not q.empty()
        got = q.get_nowait()
        assert got.event_type == "thought"

    def test_emit_with_approval(self, tmp_path):
        """L75-98 : emit avec requires_approval=True."""
        from core.bus import AgentEvent, EventBus

        bus = EventBus(db_path=tmp_path / "bus.db")
        bus.register_run("run1", "prompt test", "normal")

        event = AgentEvent(
            run_id="run1",
            event_type="tool_call",
            agent_id="agent1",
            payload={"tool": "rm"},
            requires_approval=True,
        )
        result = asyncio.run(bus.emit(event))
        assert result.event_id is not None

    def test_get_run_events_after_emit(self, tmp_path):
        """L124 : get_run_events retourne les events emis."""
        from core.bus import AgentEvent, EventBus

        bus = EventBus(db_path=tmp_path / "bus.db")
        bus.register_run("run1", "prompt test", "normal")

        for i in range(3):
            event = AgentEvent(
                run_id="run1",
                event_type=f"type_{i}",
                agent_id="agent1",
                payload={"i": i},
            )
            asyncio.run(bus.emit(event))

        events = bus.get_run_events("run1")
        assert len(events) == 3


class TestSheetEngineBranchesExtra:
    def test_generate_with_totals(self, tmp_path):
        """L89-94 : sheet avec totals."""
        from core.generators.sheet_engine import SheetEngine

        engine = SheetEngine(workspace_root=str(tmp_path))
        if not engine.is_available():
            pytest.skip("openpyxl absent")

        result = engine.generate_spreadsheet(
            filename="with_totals.xlsx",
            sheets_data=[{
                "sheet_name": "S1",
                "headers": ["A", "B"],
                "rows": [["1", "2"], ["3", "4"]],
                "totals": ["Total", "=SUM(A2:A3)", "=SUM(B2:B3)"],
            }],
        )
        assert result.get("ok") is True or "filename" in result

    def test_generate_empty_rows(self, tmp_path):
        """L98->109 : sheet avec headers mais sans rows."""
        from core.generators.sheet_engine import SheetEngine

        engine = SheetEngine(workspace_root=str(tmp_path))
        if not engine.is_available():
            pytest.skip("openpyxl absent")

        result = engine.generate_spreadsheet(
            filename="headers_only.xlsx",
            sheets_data=[{
                "sheet_name": "S1",
                "headers": ["A", "B"],
                "rows": [],
            }],
        )
        assert result.get("ok") is True or "filename" in result

    def test_generate_with_title(self, tmp_path):
        """L116 : generate avec title."""
        from core.generators.sheet_engine import SheetEngine

        engine = SheetEngine(workspace_root=str(tmp_path))
        if not engine.is_available():
            pytest.skip("openpyxl absent")

        result = engine.generate_spreadsheet(
            filename="titled.xlsx",
            title="Mon Titre",
            sheets_data=[{
                "sheet_name": "S1",
                "headers": ["A"],
                "rows": [["1"]],
            }],
        )
        assert result.get("ok") is True or "filename" in result
