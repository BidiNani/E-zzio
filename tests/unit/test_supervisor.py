"""Tests pour core/supervisor.py.

Ce module dépend de `psutil` (installé) et fait de l'introspection runtime
(sys.modules, os.environ, socket). On teste uniquement les fonctions pures
et les fonctions dont les dépendances sont mockables.

Notes :
- Le module force CPU_ONLY_ENV au chargement (effet de bord attendu).
- `system_status()` utilise psutil → testable en CI.
- `router_status()` lit sys.modules → testable.
- `forge_status()` importe dynamiquement core.creative_forge → mockable.
- `lan_ips()` fait du vrai I/O réseau → hors périmètre (skip).
"""
from __future__ import annotations

import os
import sys

import pytest

from core import supervisor

# ============================================================
# 1. Smoke + état du module
# ============================================================

class TestSmoke:
    def test_module_imports(self):
        """Le module s'importe."""
        assert supervisor is not None

    def test_cpu_only_env_forced(self):
        """Le module force CPU_ONLY_ENV à l'import."""
        assert os.environ.get("OLLAMA_NUM_GPU") == "0"
        assert os.environ.get("EZZIO_GPU_POLICY") == "cpu_ram_only"
        assert os.environ.get("EZZIO_NO_ADS") == "true"
        assert os.environ.get("EZZIO_NO_TRACKING") == "true"
        assert os.environ.get("EZZIO_NO_SPONSORS") == "true"

    def test_project_root_constant(self):
        """PROJECT_ROOT est un Path non vide."""
        assert supervisor.PROJECT_ROOT is not None
        assert str(supervisor.PROJECT_ROOT) != ""

    def test_state_roots_created(self):
        """STATE_ROOT et SNAPSHOT_ROOT existent après import."""
        assert supervisor.STATE_ROOT.exists()
        assert supervisor.SNAPSHOT_ROOT.exists()


# ============================================================
# 2. _now — timestamp (pur)
# ============================================================

class TestNow:
    def test_returns_string(self):
        """_now() retourne une chaîne."""
        ts = supervisor._now()
        assert isinstance(ts, str)

    def test_format_like_iso(self):
        """Format ISO-like (%Y-%m-%dT%H:%M:%S)."""
        ts = supervisor._now()
        assert len(ts) >= 19
        assert "T" in ts
        assert ts.count("-") >= 2


# ============================================================
# 3. _safe_call — capture d'exception (pur)
# ============================================================

class TestSafeCall:
    def test_success(self):
        """Fonction qui retourne une valeur -> ok=True."""
        result = supervisor._safe_call("test_ok", lambda: 42)
        assert result["ok"] is True
        assert result["name"] == "test_ok"
        assert result["data"] == 42

    def test_success_with_dict(self):
        """Fonction qui retourne un dict."""
        result = supervisor._safe_call("test_dict", lambda: {"a": 1})
        assert result["ok"] is True
        assert result["data"] == {"a": 1}

    def test_exception_captured(self):
        """Fonction qui lève -> ok=False + error."""
        def _boom():
            raise ValueError("boom")

        result = supervisor._safe_call("test_boom", _boom)
        assert result["ok"] is False
        assert result["name"] == "test_boom"
        assert "error" in result
        assert "boom" in result["error"]

    def test_exception_does_not_propagate(self):
        """L'exception ne remonte pas."""
        # Si _safe_call n'attrape pas, le test échoue
        result = supervisor._safe_call("test", lambda: 1 / 0)
        assert result["ok"] is False
        assert "division" in result["error"].lower()


# ============================================================
# 4. system_status — état système (psutil)
# ============================================================

class TestSystemStatus:
    def test_returns_dict(self):
        """system_status() retourne un dict."""
        result = supervisor.system_status()
        assert isinstance(result, dict)

    def test_required_sections(self):
        """Contient les sections attendues."""
        result = supervisor.system_status()
        for key in ["time", "python", "project_root", "cpu", "ram", "disk", "lan_ips", "env_policy"]:
            assert key in result, f"section manquante : {key}"

    def test_cpu_section(self):
        """La section cpu contient physical/logical cores + percent."""
        result = supervisor.system_status()
        cpu = result["cpu"]
        assert "physical_cores" in cpu
        assert "logical_cores" in cpu
        assert "percent" in cpu
        # Valeurs numériques plausibles
        assert isinstance(cpu["percent"], (int, float))
        assert 0 <= cpu["percent"] <= 100

    def test_ram_section(self):
        """La section ram contient total_gb, available_gb, used_percent."""
        result = supervisor.system_status()
        ram = result["ram"]
        assert "total_gb" in ram
        assert "available_gb" in ram
        assert "used_percent" in ram
        assert ram["total_gb"] > 0

    def test_disk_section(self):
        """La section disk contient total_gb, free_gb, used_percent."""
        result = supervisor.system_status()
        disk = result["disk"]
        assert "total_gb" in disk
        assert "free_gb" in disk
        assert "used_percent" in disk

    def test_env_policy_reflects_forced_values(self):
        """env_policy reflète les valeurs CPU_ONLY forcées."""
        result = supervisor.system_status()
        policy = result["env_policy"]
        assert policy["OLLAMA_NUM_GPU"] == "0"
        assert policy["EZZIO_GPU_POLICY"] == "cpu_ram_only"
        assert policy["EZZIO_NO_ADS"] == "true"

    def test_lan_ips_is_list(self):
        """lan_ips est une liste (possiblement vide en CI)."""
        result = supervisor.system_status()
        assert isinstance(result["lan_ips"], list)


# ============================================================
# 5. router_status — introspection sys.modules
# ============================================================

class TestRouterStatus:
    def test_without_web_server(self, monkeypatch):
        """Sans module web_server chargé -> error."""
        monkeypatch.delitem(sys.modules, "web_server", raising=False)
        result = supervisor.router_status()
        assert isinstance(result, dict)
        assert "error" in result

    def test_with_web_server_no_report(self, monkeypatch):
        """web_server présent mais sans router_load_report -> error."""
        fake_web = type(sys)("web_server")
        # On ne met PAS router_load_report
        monkeypatch.setitem(sys.modules, "web_server", fake_web)
        result = supervisor.router_status()
        assert "error" in result

    def test_with_web_server_and_report(self, monkeypatch):
        """web_server avec router_load_report -> loaded/failed counts."""
        fake_web = type(sys)("web_server")
        fake_web.router_load_report = {
            "loaded": ["router_a", "router_b"],
            "failed": {"router_c": "import error"},
        }
        monkeypatch.setitem(sys.modules, "web_server", fake_web)
        result = supervisor.router_status()
        assert result["loaded_count"] == 2
        assert result["failed_count"] == 1
        assert "router_a" in result["loaded"]
        assert "router_c" in result["failed"]


# ============================================================
# 6. forge_status — import dynamique
# ============================================================

class TestForgeStatus:
    def test_returns_dict(self):
        """forge_status() retourne un dict (ok ou erreur)."""
        result = supervisor.forge_status()
        assert isinstance(result, dict)

    def test_mockable(self, monkeypatch):
        """Si core.creative_forge.status lève, on capture l'erreur."""
        # Simuler un import qui échoue
        import builtins
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "core.creative_forge":
                raise ImportError("simulated")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        result = supervisor.forge_status()
        assert isinstance(result, dict)
        # Soit c'est un dict d'erreur, soit le module retourne ok=False
        # On vérifie juste qu'on n'a pas crashé
