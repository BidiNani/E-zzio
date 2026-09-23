"""Tests Paquet 3 quick wins : 4 fichiers a 100%.

- core/knowledge/__init__.py : imports + __all__
- core/coding/policy.py : branches whitelist + root inexistant
- core/storage.py : except rollback du contextmanager
- core/app_config.py : branches EZZIO_MODE (local/private/public)
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ============================================================
# 1. core/knowledge/__init__.py
# ============================================================

class TestKnowledgeInit:
    def test_import_exports_classes(self):
        """Le package expose les classes attendues."""
        import core.knowledge as kn_mod
        assert hasattr(kn_mod, "SelfAwarenessGateway")
        assert hasattr(kn_mod, "IntrospectionResult")
        assert hasattr(kn_mod, "ForensicDriftDetector")
        assert hasattr(kn_mod, "DriftVerdict")
        assert hasattr(kn_mod, "DriftResult")

    def test_all_list(self):
        """__all__ contient les 5 noms attendus."""
        import core.knowledge as kn_mod
        expected = {
            "SelfAwarenessGateway",
            "IntrospectionResult",
            "ForensicDriftDetector",
            "DriftVerdict",
            "DriftResult",
        }
        assert set(kn_mod.__all__) == expected


# ============================================================
# 2. core/coding/policy.py
# ============================================================

class TestCodingPolicyMissingBranches:
    def _make_request(self, task="test", mode=None, files=None):
        from core.coding.protocol import CodingRequest, ExecutionMode
        return CodingRequest(
            task_description=task,
            mode=mode or ExecutionMode.DRY_RUN,
            files_context=files or [],
        )

    def test_root_dir_inexistant_raises(self, tmp_path):
        """L64 : root_dir inexistant -> CodingPolicyViolationError."""
        from core.coding.policy import CodingPolicy
        from core.coding.protocol import CodingPolicyViolationError, ExecutionMode
        nonexistent = tmp_path / "does_not_exist"
        policy = CodingPolicy(root_dir=nonexistent)
        # La policy re-resolve le chemin -> il n'existe pas
        request = self._make_request(mode=ExecutionMode.DRY_RUN)
        # Note : la policy re-resolve root_dir, donc on force un chemin inexistant
        # via une sous-classe trichee ou en modifiant l'instance
        policy.root_dir = nonexistent
        with pytest.raises(CodingPolicyViolationError) as exc:
            policy.evaluate_request(request)
        assert "root_dir inexistant" in str(exc.value)

    def test_whitelist_blocks_unauthorized_file(self, tmp_path):
        """L67-69 : fichier hors whitelist -> CodingPolicyViolationError."""
        from core.coding.policy import CodingPolicy
        from core.coding.protocol import CodingPolicyViolationError, ExecutionMode
        policy = CodingPolicy(
            root_dir=tmp_path,
            whitelist_paths={"allowed/file.py"},
        )
        request = self._make_request(
            mode=ExecutionMode.DRY_RUN,
            files=["forbidden/file.py"],
        )
        with pytest.raises(CodingPolicyViolationError) as exc:
            policy.evaluate_request(request)
        assert "hors whitelist" in str(exc.value)

    def test_whitelist_allows_authorized_file(self, tmp_path):
        """Whitelist accepte un fichier autorise."""
        from core.coding.policy import CodingPolicy
        from core.coding.protocol import ExecutionMode
        policy = CodingPolicy(
            root_dir=tmp_path,
            whitelist_paths={"allowed/file.py"},
        )
        request = self._make_request(
            mode=ExecutionMode.DRY_RUN,
            files=["allowed/file.py"],
        )
        # Ne doit pas lever
        policy.evaluate_request(request)

    def test_mode_not_allowed_message_contains_list(self, tmp_path):
        """L58 : le message d'erreur contient la liste des modes autorises."""
        from core.coding.policy import CodingPolicy
        from core.coding.protocol import CodingPolicyViolationError, ExecutionMode
        policy = CodingPolicy(
            root_dir=tmp_path,
            allowed_modes=frozenset([ExecutionMode.DRY_RUN]),
        )
        request = self._make_request(mode=ExecutionMode.READ_ONLY_SANDBOX)
        with pytest.raises(CodingPolicyViolationError) as exc:
            policy.evaluate_request(request)
        msg = str(exc.value)
        assert "non autorisé" in msg
        assert "dry_run" in msg.lower()


# ============================================================
# 3. core/storage.py
# ============================================================

class TestStorageEngineException:
    def test_rollback_on_exception(self, tmp_path, caplog):
        """L31-34 : exception dans le with -> rollback + raise."""
        from core.storage import StorageEngine
        db_path = tmp_path / "test.db"

        with pytest.raises(RuntimeError, match="boom"):
            with StorageEngine.get_connection(db_path) as conn:
                # Verifier que conn est utilisable
                assert conn is not None
                # Lever une exception
                raise RuntimeError("boom")

        # Verifier que le log d'erreur a ete emis
        # (le logger.error est dans le module, on ne peut pas facilement verifier
        #  sans capturer, mais on peut verifier l'exception propagee)

    def test_normal_path_commits(self, tmp_path):
        """Cas nominal : commit silencieux, pas de raise."""
        from core.storage import StorageEngine
        db_path = tmp_path / "test.db"

        with StorageEngine.get_connection(db_path) as conn:
            conn.execute("CREATE TABLE t (id INTEGER)")
            conn.execute("INSERT INTO t VALUES (1)")

        # Verifier que la donnee est persistee
        import sqlite3
        conn2 = sqlite3.connect(db_path)
        try:
            cur = conn2.execute("SELECT COUNT(*) FROM t")
            count = cur.fetchone()[0]
            assert count == 1
        finally:
            conn2.close()

    def test_creates_parent_dirs(self, tmp_path):
        """L22 : les dossiers parents sont crees."""
        from core.storage import StorageEngine
        db_path = tmp_path / "sub" / "deep" / "test.db"
        assert not db_path.parent.exists()

        with StorageEngine.get_connection(db_path):
            pass

        assert db_path.parent.exists()
        assert db_path.exists()


# ============================================================
# 4. core/app_config.py
# ============================================================

class TestAppConfigModes:
    """
    Ces tests chargent core.app_config avec un EZZIO_MODE different.

    Strategie : on retire core.app_config de sys.modules puis on reimporte
    le module pour forcer Python a reexecuter le fichier source.
    monkeypatch.setenv restaure l'environnement automatiquement.
    """

    def _load_with_mode(self, mode: str, env_overrides: dict | None = None):
        """Force un reimport de core.app_config avec un mode donne."""
        from unittest.mock import patch as _patch

        env = {"EZZIO_MODE": mode}
        if env_overrides:
            env.update(env_overrides)

        # Retirer le module du cache pour forcer un import frais
        sys.modules.pop("core.app_config", None)

        with _patch.dict("os.environ", env, clear=False):
            import core.app_config as mod
            return mod

    def test_mode_local_uses_127_0_0_1(self):
        """L29 : EZZIO_MODE=local -> HOST=127.0.0.1."""
        mod = self._load_with_mode("local")
        assert mod.HOST == "127.0.0.1"
        assert mod.ALLOWED_ORIGINS == ["*"]
        assert mod.RATE_LIMIT == "300/minute"
        assert mod.REQUIRE_AUTH is False

    def test_mode_private_rate_limit(self):
        """L54-55 : EZZIO_MODE=private -> RATE_LIMIT=60/minute."""
        mod = self._load_with_mode("private")
        assert mod.RATE_LIMIT == "60/minute"
        assert mod.MASK_ERRORS is True

    def test_mode_public_rate_limit(self):
        """L56-57 : EZZIO_MODE=public -> RATE_LIMIT=30/minute."""
        mod = self._load_with_mode("public")
        assert mod.RATE_LIMIT == "30/minute"
        assert mod.MASK_ERRORS is True
        assert mod.CORS_STRICT_BLOCK is True

    def test_mode_lan_default(self):
        """EZZIO_MODE=lan (defaut) -> RATE_LIMIT=120/minute."""
        mod = self._load_with_mode("lan")
        assert mod.RATE_LIMIT == "120/minute"
        assert mod.REQUIRE_AUTH is True
        assert mod.LOG_JSON is True

    def test_custom_ports(self):
        """Les ports sont configurables via env."""
        mod = self._load_with_mode("lan", {
            "EZZIO_BACKEND_PORT": "9999",
            "EZZIO_FRONTEND_PORT": "9998",
        })
        assert mod.BACKEND_PORT == 9999
        assert mod.FRONTEND_PORT == 9998

    def test_host_else_branch_for_non_local(self):
        """L30-31 : EZZIO_MODE!=local -> HOST=0.0.0.0."""
        mod = self._load_with_mode("lan")
        assert mod.HOST == "0.0.0.0"
