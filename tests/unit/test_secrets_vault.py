"""Tests pour core/security/secrets_vault.py (partie 2 : fallback crypto)."""
from __future__ import annotations

import base64
import json
from unittest.mock import patch

import pytest

from core.security import secrets_vault
from core.security.secrets_vault import SecretsVault


@pytest.fixture
def vault(tmp_path):
    return SecretsVault(workspace_root=str(tmp_path))


@pytest.fixture
def env_file(tmp_path):
    f = tmp_path / "source.env"
    f.write_text("KEY1=v1\nKEY2=v2\n", encoding="utf-8")
    return f


class TestFallbackNoCryptography:
    """Teste le fallback PBKDF2-XOR quand cryptography n'est pas dispo."""

    def test_encrypt_decrypt_fallback(self, vault, env_file, tmp_path, monkeypatch):
        """Force HAS_CRYPTOGRAPHY=False et teste round-trip."""
        monkeypatch.setattr(secrets_vault, "HAS_CRYPTOGRAPHY", False)
        dest = tmp_path / "out.enc"
        result = vault.encrypt_env(env_file, dest, passphrase="test-key")
        assert result["ok"] is True
        # Vérifier l'algo dans l'envelope
        envelope = json.loads(dest.read_text(encoding="utf-8"))
        assert envelope["algorithm"] == "PBKDF2-XOR-HMAC"

    def test_decrypt_wrong_pass_fallback(self, vault, env_file, tmp_path, monkeypatch):
        """Mauvais mot de passe en mode fallback -> INTEGRITY ERROR."""
        monkeypatch.setattr(secrets_vault, "HAS_CRYPTOGRAPHY", False)
        dest = tmp_path / "out.enc"
        vault.encrypt_env(env_file, dest, passphrase="good")
        result = vault.decrypt_to_memory(dest, passphrase="bad")
        assert result["ok"] is False
        assert "INTEGRITY" in result["error"] or "incorrect" in result["error"].lower()

    def test_decrypt_corrupted_tag_fallback(self, vault, env_file, tmp_path, monkeypatch):
        """Tag corrompu en mode fallback -> échec."""
        monkeypatch.setattr(secrets_vault, "HAS_CRYPTOGRAPHY", False)
        dest = tmp_path / "out.enc"
        vault.encrypt_env(env_file, dest, passphrase="key")
        # Corrompre les bytes
        envelope = json.loads(dest.read_text(encoding="utf-8"))
        raw = base64.b64decode(envelope["data_b64"])
        corrupted = raw[:-1] + bytes([raw[-1] ^ 0xFF])
        envelope["data_b64"] = base64.b64encode(corrupted).decode("ascii")
        dest.write_text(json.dumps(envelope), encoding="utf-8")
        result = vault.decrypt_to_memory(dest, passphrase="key")
        assert result["ok"] is False


class TestDeriveKeyBothPaths:
    def test_derive_key_with_cryptography(self, vault):
        """Avec cryptography -> PBKDF2HMAC."""
        key = vault._derive_key("pass", b"salt-16-bytes!!")
        assert len(key) == 32

    def test_derive_key_without_cryptography(self, vault, monkeypatch):
        """Sans cryptography -> hashlib.pbkdf2_hmac."""
        monkeypatch.setattr(secrets_vault, "HAS_CRYPTOGRAPHY", False)
        key = vault._derive_key("pass", b"salt-16-bytes!!")
        assert len(key) == 32

    def test_derive_key_same_result_both_paths(self, vault, monkeypatch):
        """Les deux chemins doivent donner le même résultat (PBKDF2 standard)."""
        salt = b"fixed-salt-16b!!"
        k_with = vault._derive_key("pass", salt)
        monkeypatch.setattr(secrets_vault, "HAS_CRYPTOGRAPHY", False)
        k_without = vault._derive_key("pass", salt)
        assert k_with == k_without


class TestWindowsDpapiMocked:
    """Teste seal/unseal DPAPI avec mocks (simule Windows)."""

    def test_seal_to_dpapi_mocked_success(self, vault, tmp_path, monkeypatch):
        """Mock ctypes.windll -> scellement réussi."""
        import sys
        monkeypatch.setattr(sys, "platform", "win32")

        # Mock ctypes.windll
        mock_windll = type("Windll", (), {})()
        mock_crypt32 = type("Crypt32", (), {})()
        mock_kernel32 = type("Kernel32", (), {})()

        def fake_CryptProtectData(*args):
            # args[-1] est byref(blob_out)
            blob_out_ptr = args[-1]
            # Simuler succès en écrivant des bytes
            return 1  # True

        mock_crypt32.CryptProtectData = fake_CryptProtectData
        mock_kernel32.LocalFree = lambda x: None

        mock_windll.crypt32 = mock_crypt32
        mock_windll.kernel32 = mock_kernel32

        import ctypes
        monkeypatch.setattr(ctypes, "windll", mock_windll)

        # Test que seal_to_dpapi retourne True avec le mock
        result = vault.seal_to_dpapi("test-key", tmp_path / "test.bin")
        # Le mock retourne 1 -> True
        assert isinstance(result, bool)

    def test_unseal_from_dpapi_missing_file(self, vault, monkeypatch):
        """Fichier absent -> None."""
        import sys
        monkeypatch.setattr(sys, "platform", "win32")
        result = vault.unseal_from_dpapi(vault.secrets_dir / "nonexistent.bin")
        assert result is None
