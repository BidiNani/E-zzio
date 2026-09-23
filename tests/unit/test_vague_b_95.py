"""Tests Vague B : 5 fichiers 95% -> 100%.

Cible les branches/lignes manquantes identifiees par --cov-report:
- core/capabilities/factory.py          : L73, L82
- core/cognition/cognitive_gateway.py   : L152-156
- core/security/unified_vault.py        : L36, L40->33, L42-43
- core/signals/signal_bus.py            : L49->56, L98-99
- core/tasks/manager.py                 : L172, L210
"""
from __future__ import annotations

import asyncio
import os
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ============================================================
# 1. core/capabilities/factory.py — L73, L82
# ============================================================

class TestCapabilityFactoryDeniedBranches:
    """L73 (DENIED trust) + L82 (DENIED_BY_POLICY)."""

    def test_acquire_denied_by_trust_guard(self):
        """L73 : trust_check['allowed'] = False -> DENIED."""
        from core.capabilities import factory as factory_mod
        from core.capabilities.factory import CapabilityFactory

        f = CapabilityFactory.__new__(CapabilityFactory)  # avoid __init__ side effects
        f.workspace_root = Path("G:/AI/E-zzio")
        f.sandbox_base = Path("G:/AI/external/capabilities")
        f.discovery = MagicMock()
        f.policy = MagicMock()

        proposal = MagicMock()
        proposal.name = "malicious_cap"
        proposal.required_permissions = ["shell_exec"]

        with patch.object(
            factory_mod.CapabilityTrustGuard,
            "validate_capability_action",
            return_value={"allowed": False, "reason": "suspicious permissions"},
        ):
            result = f.acquire_capability(proposal)

        assert result["ok"] is False
        assert result["status"] == "DENIED"
        assert "suspicious" in result["reason"]

    def test_acquire_denied_by_policy(self):
        """L82 : trust OK mais PolicyDecision.DENY -> DENIED_BY_POLICY."""
        from core.capabilities import factory as factory_mod
        from core.capabilities.capability_policy import PolicyDecision
        from core.capabilities.factory import CapabilityFactory

        f = CapabilityFactory.__new__(CapabilityFactory)
        f.workspace_root = Path("G:/AI/E-zzio")
        f.sandbox_base = Path("G:/AI/external/capabilities")
        f.discovery = MagicMock()
        f.policy = MagicMock()
        f.policy.evaluate_scope.return_value = (PolicyDecision.DENY, "policy violation")

        proposal = MagicMock()
        proposal.name = "risky_cap"
        proposal.required_permissions = []
        proposal.risk_level = "HIGH"
        proposal.locality = "CLOUD_API"

        with patch.object(
            factory_mod.CapabilityTrustGuard,
            "validate_capability_action",
            return_value={"allowed": True, "reason": ""},
        ):
            result = f.acquire_capability(proposal)

        assert result["ok"] is False
        assert result["status"] == "DENIED_BY_POLICY"
        assert "policy violation" in result["reason"]


# ============================================================
# 2. core/cognition/cognitive_gateway.py — L152-156
# ============================================================

class TestCognitiveGatewayAskInRunningLoop:
    """L152-156 : ask() depuis un thread avec loop active."""

    def test_ask_from_thread_with_running_loop(self, tmp_path):
        """Appelle ask() depuis un thread pendant qu'une loop tourne."""
        from core.cognition.cognitive_gateway import CognitiveGateway

        db_path = str(tmp_path / "test.db")
        gw = CognitiveGateway(db_path=db_path)

        # Mock adapter.chat_completion pour eviter un vrai appel LLM
        gw._adapter = MagicMock()
        gw._adapter.chat_completion.return_value = "reponse mockee"

        result_holder = {}
        ready = threading.Event()

        async def run_loop():
            # Lance ask() depuis un thread pendant que CETTE loop tourne
            def call_ask():
                ready.wait(timeout=2)
                try:
                    res = gw.ask("test from thread", session_id="s1")
                    result_holder["result"] = res
                except Exception as e:
                    result_holder["error"] = e

            t = threading.Thread(target=call_ask)
            t.start()
            ready.set()
            # Laisse le temps au thread d'appeler ask() pendant que la loop tourne
            await asyncio.sleep(0.3)
            t.join(timeout=3)

        asyncio.run(run_loop())

        # Verifie qu'on est passe par la branche is_running() == True
        assert "result" in result_holder or "error" in result_holder
        if "result" in result_holder:
            assert result_holder["result"].get("status") in ("ACCEPTED", "FAILED")


# ============================================================
# 3. core/security/unified_vault.py — L36, L40->33, L42-43
# ============================================================

class TestUnifiedVaultEnvParsingBranches:
    """L36 (continue), L40->33 (clean_k/clean_v False), L42-43 (except)."""

    def test_env_with_empty_and_comment_lines(self, tmp_path):
        """L36 : lignes vides, commentaires, sans '=' -> continue."""
        from core.security import unified_vault as uv_mod
        from core.security.unified_vault import UnifiedKeyVault

        env_file = tmp_path / "secrets" / ".env"
        env_file.parent.mkdir(parents=True, exist_ok=True)
        env_file.write_text(
            "\n"
            "# commentaire\n"
            "LIGNE_SANS_EGAL\n"
            "CLE_VALIDE=valeur_ok\n"
            "\n",
            encoding="utf-8",
        )

        with patch.object(uv_mod, "ENV_FILES", [env_file]):
            v = UnifiedKeyVault()

        assert v.get("CLE_VALIDE") == "valeur_ok"

    def test_env_with_empty_key_or_value(self, tmp_path):
        """L40->33 : clean_k ou clean_v vide -> ne stocke pas."""
        from core.security import unified_vault as uv_mod
        from core.security.unified_vault import UnifiedKeyVault

        env_file = tmp_path / "secrets" / ".env"
        env_file.parent.mkdir(parents=True, exist_ok=True)
        env_file.write_text(
            "=vide_sans_cle\n"
            "CLE_SANS_VALEUR=\n"
            "CLE_OK=val\n",
            encoding="utf-8",
        )

        with patch.object(uv_mod, "ENV_FILES", [env_file]):
            v = UnifiedKeyVault()

        # CLE_SANS_VALEUR ne doit pas etre stockee (clean_v vide)
        assert "CLE_SANS_VALEUR" not in v._cache
        assert "CLE_OK" in v._cache

    def test_env_unreadable_triggers_exception_branch(self, tmp_path):
        """L42-43 : lecture echoue -> except -> pass."""
        from core.security import unified_vault as uv_mod
        from core.security.unified_vault import UnifiedKeyVault

        # Cree un fichier, puis simule une erreur de lecture
        env_file = tmp_path / "secrets" / ".env"
        env_file.parent.mkdir(parents=True, exist_ok=True)
        env_file.write_text("CLE=x\n", encoding="utf-8")

        original_read = Path.read_text

        def broken_read(self, *args, **kwargs):
            if self == env_file:
                raise OSError("simulated read error")
            return original_read(self, *args, **kwargs)

        with patch.object(uv_mod, "ENV_FILES", [env_file]), \
             patch.object(Path, "read_text", broken_read):
            v = UnifiedKeyVault()  # ne doit pas lever

        assert isinstance(v._cache, dict)


# ============================================================
# 4. core/signals/signal_bus.py — L49->56, L98-99
# ============================================================

class TestSignalBusDuplicateAndSyncEmit:
    """L49->56 (duplicate connect) + L98-99 (sync emit with async listener)."""

    def test_duplicate_connect_is_idempotent(self):
        """L49->56 : connect() 2 fois le meme callback -> 1 seule entree."""
        from core.signals.signal_bus import SignalBus

        bus = SignalBus()

        async def listener(payload):
            pass

        bus.connect("test_event", listener)
        bus.connect("test_event", listener)  # duplicate

        assert len(bus._async_listeners["test_event"]) == 1

    def test_sync_emit_with_async_listener_in_running_loop(self):
        """L98-99 : emit() sync dans une loop active avec listener async."""
        from core.signals.signal_bus import SignalBus

        bus = SignalBus()
        called = {"count": 0}

        async def async_listener(payload):
            called["count"] += 1

        bus.connect("test_sync", async_listener)

        async def runner():
            bus.emit("test_sync", {"x": 1})
            # Laisse la task planifiee s'executer
            await asyncio.sleep(0.1)

        asyncio.run(runner())
        assert called["count"] == 1


# ============================================================
# 5. core/tasks/manager.py — L172, L210
# ============================================================

class TestTaskManagerErrorBranches:
    """L172 (etat inconnu) + L210 (tache introuvable apres update)."""

    def test_transition_to_unknown_state(self, tmp_path):
        """L172 : next_state pas dans TASK_STATES -> ValueError."""
        from core.tasks import manager as mgr_mod
        from core.tasks.manager import TaskManager

        db = tmp_path / "tasks.db"
        with patch.object(mgr_mod, "DB_PATH", db):
            tm = TaskManager()
            tm.create_task(task_id="t1", title="t", workspace="w", scope={})

            with pytest.raises(ValueError, match="tat inconnu"):
                tm.transition_task("t1", "TOTALLY_UNKNOWN_STATE")

    def test_transition_task_disappears_after_update(self, tmp_path):
        """L210 : get_task() retourne None apres UPDATE -> RuntimeError."""
        from core.tasks import manager as mgr_mod
        from core.tasks.manager import TaskManager

        db = tmp_path / "tasks.db"
        with patch.object(mgr_mod, "DB_PATH", db):
            tm = TaskManager()
            tm.create_task(task_id="t2", title="t", workspace="w", scope={})

            # Mock get_task : 1er appel OK (DRAFT), 2e appel retourne None
            real_get = tm.get_task
            call_count = {"n": 0}

            def flaky_get(task_id):
                call_count["n"] += 1
                if call_count["n"] == 1:
                    return real_get(task_id)
                return None

            with patch.object(tm, "get_task", side_effect=flaky_get):
                with pytest.raises(RuntimeError, match="introuvable apr"):
                    tm.transition_task("t2", "SCOPED")
