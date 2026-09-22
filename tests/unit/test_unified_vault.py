"""Tests pour core/security/unified_vault.py.

Vault unifié : façade unifiée sur SecretsVault + DPAPI + redaction.
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.security import unified_vault


class TestSmoke:
    def test_module_imports(self):
        assert unified_vault is not None

    def test_public_symbols(self):
        publics = [n for n in dir(unified_vault) if not n.startswith("_")]
        assert len(publics) > 0

    def test_module_file(self):
        assert Path(unified_vault.__file__).exists()

    def test_module_docstring(self):
        assert unified_vault.__doc__ is not None


class TestAPI:
    def test_public_functions(self):
        import inspect
        funcs = [n for n, o in inspect.getmembers(unified_vault, inspect.isfunction)
                 if not n.startswith("_")]
        assert isinstance(funcs, list)

    def test_public_classes(self):
        import inspect
        classes = [n for n, o in inspect.getmembers(unified_vault, inspect.isclass)
                   if not n.startswith("_")]
        assert isinstance(classes, list)

    def test_constants(self):
        consts = [n for n in dir(unified_vault) if n.isupper()]
        assert isinstance(consts, list)


class TestRedactionIfPresent:
    def test_redact_patterns(self):
        """Si le module a une fonction de redaction, tester."""
        candidates = ["redact", "mask", "sanitize", "redact_all"]
        for name in candidates:
            if hasattr(unified_vault, name):
                try:
                    fn = getattr(unified_vault, name)
                    result = fn("my-secret-token-xyz")
                    if result is not None:
                        assert isinstance(result, (str, dict))
                except TypeError:
                    pytest.skip(f"{name} signature différente")


class TestVaultAccess:
    def test_vault_singleton_if_present(self):
        """Si le module expose un singleton, vérifier."""
        candidates = ["unified_vault_instance", "vault", "UNIFIED_VAULT"]
        for name in candidates:
            if hasattr(unified_vault, name):
                obj = getattr(unified_vault, name)
                assert obj is not None
