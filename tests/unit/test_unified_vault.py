"""Tests réels pour core/security/unified_vault.py.

UnifiedKeyVault : singleton centralisant l'accès aux clés avec rotation
multi-clés. Lit .env + os.environ.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.security import unified_vault
from core.security.unified_vault import UnifiedKeyVault, key_vault

# ============================================================
# 1. Smoke
# ============================================================

class TestSmoke:
    def test_module_imports(self):
        assert unified_vault is not None

    def test_singleton_exists(self):
        assert key_vault is not None
        assert isinstance(key_vault, UnifiedKeyVault)

    def test_module_docstring(self):
        assert unified_vault.__doc__ is not None


# ============================================================
# 2. Init + reload
# ============================================================

class TestInitReload:
    def test_init_creates_cache(self, monkeypatch):
        # Neutraliser les fichiers .env
        monkeypatch.setattr(unified_vault, "ENV_FILES", [])
        vault = UnifiedKeyVault()
        assert hasattr(vault, "_cache")
        assert hasattr(vault, "_key_iterators")

    def test_reload_clears_cache(self, monkeypatch):
        monkeypatch.setattr(unified_vault, "ENV_FILES", [])
        vault = UnifiedKeyVault()
        vault._cache["FAKE_KEY"] = "value"
        vault.reload()
        # Le cache a été rechargé depuis os.environ
        assert "FAKE_KEY" not in vault._cache

    def test_reload_reads_env_files(self, tmp_path, monkeypatch):
        env_file = tmp_path / "test.env"
        env_file.write_text("TEST_KEY=test_value\n")
        monkeypatch.setattr(unified_vault, "ENV_FILES", [env_file])
        vault = UnifiedKeyVault()
        assert vault._cache.get("TEST_KEY") == "test_value"


# ============================================================
# 3. get
# ============================================================

class TestGet:
    def test_get_from_cache(self, monkeypatch):
        monkeypatch.setattr(unified_vault, "ENV_FILES", [])
        vault = UnifiedKeyVault()
        vault._cache["MY_KEY"] = "my-value"
        assert vault.get("MY_KEY") == "my-value"

    def test_get_returns_default(self, monkeypatch):
        monkeypatch.setattr(unified_vault, "ENV_FILES", [])
        vault = UnifiedKeyVault()
        assert vault.get("MISSING_KEY", default="fallback") == "fallback"

    def test_get_default_empty(self, monkeypatch):
        monkeypatch.setattr(unified_vault, "ENV_FILES", [])
        vault = UnifiedKeyVault()
        assert vault.get("MISSING_KEY") == ""

    def test_get_strips_value(self, monkeypatch):
        monkeypatch.setattr(unified_vault, "ENV_FILES", [])
        vault = UnifiedKeyVault()
        vault._cache["STRIP_KEY"] = "  value with spaces  "
        assert vault.get("STRIP_KEY") == "value with spaces"

    def test_get_env_priority(self, monkeypatch):
        """os.environ a priorité sur le cache."""
        monkeypatch.setattr(unified_vault, "ENV_FILES", [])
        vault = UnifiedKeyVault()
        vault._cache["PRIORITY_KEY"] = "from-cache"
        monkeypatch.setenv("PRIORITY_KEY", "from-env")
        assert vault.get("PRIORITY_KEY") == "from-env"


# ============================================================
# 4. get_bool
# ============================================================

class TestGetBool:
    @pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "y", "on"])
    def test_true_variants(self, monkeypatch, value):
        monkeypatch.setattr(unified_vault, "ENV_FILES", [])
        vault = UnifiedKeyVault()
        vault._cache["BOOL_KEY"] = value
        assert vault.get_bool("BOOL_KEY") is True

    @pytest.mark.parametrize("value", ["0", "false", "no", "off", "random"])
    def test_false_variants(self, monkeypatch, value):
        monkeypatch.setattr(unified_vault, "ENV_FILES", [])
        vault = UnifiedKeyVault()
        vault._cache["BOOL_KEY"] = value
        assert vault.get_bool("BOOL_KEY") is False

    def test_default_true(self, monkeypatch):
        monkeypatch.setattr(unified_vault, "ENV_FILES", [])
        vault = UnifiedKeyVault()
        assert vault.get_bool("MISSING", default=True) is True

    def test_default_false(self, monkeypatch):
        monkeypatch.setattr(unified_vault, "ENV_FILES", [])
        vault = UnifiedKeyVault()
        assert vault.get_bool("MISSING", default=False) is False


# ============================================================
# 5. get_all_keys_for_provider
# ============================================================

class TestGetAllKeysForProvider:
    def test_empty_for_unknown(self, monkeypatch):
        monkeypatch.setattr(unified_vault, "ENV_FILES", [])
        vault = UnifiedKeyVault()
        vault._cache.clear()
        assert vault.get_all_keys_for_provider("unknown_provider") == []

    def test_gemini_patterns(self, monkeypatch):
        monkeypatch.setattr(unified_vault, "ENV_FILES", [])
        vault = UnifiedKeyVault()
        vault._cache = {
            "GEMINI_API_KEY": "g1",
            "GEMINI_API_KEY_2": "g2",
            "GOOGLE_API_KEY": "goog",
            "OTHER_KEY": "x",
        }
        keys = vault.get_all_keys_for_provider("gemini")
        assert "g1" in keys
        assert "g2" in keys
        assert "goog" in keys
        assert "x" not in keys

    def test_groq_pattern(self, monkeypatch):
        monkeypatch.setattr(unified_vault, "ENV_FILES", [])
        vault = UnifiedKeyVault()
        vault._cache = {"GROQ_API_KEY": "gq1", "GROQ_API_KEY_2": "gq2"}
        keys = vault.get_all_keys_for_provider("groq")
        assert set(keys) == {"gq1", "gq2"}

    def test_openrouter_pattern(self, monkeypatch):
        monkeypatch.setattr(unified_vault, "ENV_FILES", [])
        vault = UnifiedKeyVault()
        vault._cache = {"OPENROUTER_API_KEY": "or1"}
        keys = vault.get_all_keys_for_provider("openrouter")
        assert keys == ["or1"]

    def test_generic_provider_pattern(self, monkeypatch):
        monkeypatch.setattr(unified_vault, "ENV_FILES", [])
        vault = UnifiedKeyVault()
        vault._cache = {"MYAI_API_KEY": "gen1"}
        keys = vault.get_all_keys_for_provider("myai")
        assert "gen1" in keys

    def test_deduplicates_keys(self, monkeypatch):
        """Les valeurs dupliquées sont déduplicées."""
        monkeypatch.setattr(unified_vault, "ENV_FILES", [])
        vault = UnifiedKeyVault()
        vault._cache = {"GEMINI_API_KEY": "same", "GEMINI_API_KEY_2": "same"}
        keys = vault.get_all_keys_for_provider("gemini")
        assert keys == ["same"]

    def test_skips_empty_values(self, monkeypatch):
        monkeypatch.setattr(unified_vault, "ENV_FILES", [])
        vault = UnifiedKeyVault()
        vault._cache = {"GEMINI_API_KEY": "", "GEMINI_API_KEY_2": "valid"}
        keys = vault.get_all_keys_for_provider("gemini")
        assert keys == ["valid"]


# ============================================================
# 6. get_provider_key (rotation)
# ============================================================

class TestGetProviderKey:
    def test_no_key_returns_empty(self, monkeypatch):
        monkeypatch.setattr(unified_vault, "ENV_FILES", [])
        vault = UnifiedKeyVault()
        vault._cache.clear()
        assert vault.get_provider_key("unknown") == ""

    def test_single_key_no_rotation(self, monkeypatch):
        monkeypatch.setattr(unified_vault, "ENV_FILES", [])
        vault = UnifiedKeyVault()
        vault._cache = {"GEMINI_API_KEY": "only"}
        assert vault.get_provider_key("gemini") == "only"
        assert vault.get_provider_key("gemini") == "only"

    def test_multi_key_rotation(self, monkeypatch):
        """Avec plusieurs clés -> rotation round-robin."""
        monkeypatch.setattr(unified_vault, "ENV_FILES", [])
        vault = UnifiedKeyVault()
        vault._cache = {"GEMINI_API_KEY": "k1", "GEMINI_API_KEY_2": "k2"}
        results = [vault.get_provider_key("gemini") for _ in range(4)]
        # Doit alterner k1, k2, k1, k2
        assert results[0] != results[1]
        assert results[0] == results[2]
        assert results[1] == results[3]


# ============================================================
# 7. is_cloud_allowed
# ============================================================

class TestIsCloudAllowed:
    def test_default_true(self, monkeypatch):
        monkeypatch.setattr(unified_vault, "ENV_FILES", [])
        vault = UnifiedKeyVault()
        vault._cache.clear()
        monkeypatch.delenv("EZZIO_CLOUD_ALLOW_SEND", raising=False)
        assert vault.is_cloud_allowed() is True

    def test_explicit_false(self, monkeypatch):
        monkeypatch.setattr(unified_vault, "ENV_FILES", [])
        vault = UnifiedKeyVault()
        vault._cache["EZZIO_CLOUD_ALLOW_SEND"] = "false"
        monkeypatch.delenv("EZZIO_CLOUD_ALLOW_SEND", raising=False)
        assert vault.is_cloud_allowed() is False

    def test_explicit_true(self, monkeypatch):
        monkeypatch.setattr(unified_vault, "ENV_FILES", [])
        vault = UnifiedKeyVault()
        vault._cache["EZZIO_CLOUD_ALLOW_SEND"] = "true"
        monkeypatch.delenv("EZZIO_CLOUD_ALLOW_SEND", raising=False)
        assert vault.is_cloud_allowed() is True
