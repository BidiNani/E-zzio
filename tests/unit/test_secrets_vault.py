"""Tests pour core/security/secrets_vault.py.

SecretsVault : chiffrement at-rest AES-256-GCM + PBKDF2 + DPAPI Windows.

Découvertes pré-test :
- HAS_CRYPTOGRAPHY booléen (cryptography installé ou non)
- seal_to_dpapi / unseal_from_dpapi : Windows uniquement (skip ailleurs)
- _derive_key : PBKDF2-HMAC-SHA256, 100k itérations, 32 bytes
- encrypt_env : crée un envelope JSON avec salt/nonce/data en base64
- decrypt_to_memory : parse le envelope et déchiffre
- Singleton global secrets_vault à l'import
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.security.secrets_vault import (
    HAS_CRYPTOGRAPHY,
    SecretsVault,
    secrets_vault,
)

# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def vault(tmp_path):
    """Vault isolé dans tmp_path."""
    return SecretsVault(workspace_root=str(tmp_path))


@pytest.fixture
def env_file(tmp_path):
    """Fichier .env factice."""
    f = tmp_path / "source.env"
    f.write_text(
        "API_KEY=secret123\n"
        "DB_PASSWORD=hunter2\n"
        "# Commentaire\n"
        "\n"
        "TOKEN=\"quoted-value\"\n",
        encoding="utf-8",
    )
    return f


# ============================================================
# 1. Smoke + constantes
# ============================================================

class TestSmoke:
    def test_module_imports(self):
        assert SecretsVault is not None

    def test_has_cryptography_flag(self):
        """HAS_CRYPTOGRAPHY est un booléen."""
        assert isinstance(HAS_CRYPTOGRAPHY, bool)

    def test_singleton_exists(self):
        assert secrets_vault is not None
        assert isinstance(secrets_vault, SecretsVault)


# ============================================================
# 2. __init__
# ============================================================

class TestInit:
    def test_creates_secrets_dir(self, tmp_path):
        """Le constructeur crée le dossier secrets/."""
        vault = SecretsVault(workspace_root=str(tmp_path))
        expected = tmp_path / "secrets"
        assert expected.exists()
        assert expected.is_dir()

    def test_stores_workspace_root(self, tmp_path):
        vault = SecretsVault(workspace_root=str(tmp_path))
        assert vault.workspace_root == tmp_path.resolve()

    def test_idempotent(self, tmp_path):
        """Deux instanciations ne plantent pas."""
        SecretsVault(workspace_root=str(tmp_path))
        SecretsVault(workspace_root=str(tmp_path))


# ============================================================
# 3. get_passphrase
# ============================================================

class TestGetPassphrase:
    def test_explicit_passphrase(self, vault):
        """Paramètre explicite a priorité."""
        assert vault.get_passphrase("explicit-key") == "explicit-key"

    def test_env_var_passphrase(self, vault, monkeypatch):
        """EZZIO_VAULT_PASSPHRASE utilisé si pas d'explicite."""
        monkeypatch.setenv("EZZIO_VAULT_PASSPHRASE", "env-key-1")
        monkeypatch.delenv("EZZIO_MASTER_KEY", raising=False)
        assert vault.get_passphrase() == "env-key-1"

    def test_env_master_key_fallback(self, vault, monkeypatch):
        """EZZIO_MASTER_KEY utilisé si EZZIO_VAULT_PASSPHRASE absent."""
        monkeypatch.delenv("EZZIO_VAULT_PASSPHRASE", raising=False)
        monkeypatch.setenv("EZZIO_MASTER_KEY", "env-key-2")
        assert vault.get_passphrase() == "env-key-2"

    def test_vault_passphrase_priority(self, vault, monkeypatch):
        """EZZIO_VAULT_PASSPHRASE > EZZIO_MASTER_KEY."""
        monkeypatch.setenv("EZZIO_VAULT_PASSPHRASE", "priority")
        monkeypatch.setenv("EZZIO_MASTER_KEY", "fallback")
        assert vault.get_passphrase() == "priority"

    def test_returns_none_without_source(self, vault, monkeypatch):
        """Aucune source -> None."""
        monkeypatch.delenv("EZZIO_VAULT_PASSPHRASE", raising=False)
        monkeypatch.delenv("EZZIO_MASTER_KEY", raising=False)
        assert vault.get_passphrase() is None

    def test_explicit_overrides_env(self, vault, monkeypatch):
        monkeypatch.setenv("EZZIO_VAULT_PASSPHRASE", "from-env")
        assert vault.get_passphrase("from-arg") == "from-arg"


# ============================================================
# 4. _derive_key
# ============================================================

class TestDeriveKey:
    def test_deterministic(self, vault):
        """Même passphrase + salt -> même clé."""
        salt = b"0123456789abcdef"
        k1 = vault._derive_key("secret", salt)
        k2 = vault._derive_key("secret", salt)
        assert k1 == k2

    def test_key_length_32_bytes(self, vault):
        """Clé de 32 bytes (AES-256)."""
        key = vault._derive_key("secret", b"salt-16-bytes!!")
        assert len(key) == 32

    def test_different_passphrase_different_key(self, vault):
        salt = b"same-salt-here!!"
        k1 = vault._derive_key("pass1", salt)
        k2 = vault._derive_key("pass2", salt)
        assert k1 != k2

    def test_different_salt_different_key(self, vault):
        k1 = vault._derive_key("same-pass", b"salt-aaaa-aaaaaaa")
        k2 = vault._derive_key("same-pass", b"salt-bbbb-bbbbbbb")
        assert k1 != k2


# ============================================================
# 5. seal_to_dpapi / unseal_from_dpapi (Windows only)
# ============================================================

class TestDpapi:
    def test_seal_non_windows_returns_false(self, vault):
        """Hors Windows -> False."""
        import sys
        if sys.platform == "win32":
            pytest.skip("Test spécifique non-Windows")
        assert vault.seal_to_dpapi("test-key") is False

    def test_unseal_non_windows_returns_none(self, vault, tmp_path):
        """Hors Windows -> None."""
        import sys
        if sys.platform == "win32":
            pytest.skip("Test spécifique non-Windows")
        f = tmp_path / "fake.bin"
        f.write_bytes(b"some bytes")
        assert vault.unseal_from_dpapi(f) is None

    def test_unseal_missing_file(self, vault):
        """Fichier absent -> None."""
        import sys
        if sys.platform != "win32":
            pytest.skip("DPAPI Windows only")
        # Sur Windows, fichier absent -> None
        assert vault.unseal_from_dpapi() is None


# ============================================================
# 6. encrypt_env / decrypt_to_memory
# ============================================================

class TestEncryptDecrypt:
    def test_encrypt_missing_source(self, vault, tmp_path):
        """Source inexistante -> ok=False."""
        result = vault.encrypt_env(
            source_file=tmp_path / "nope.env",
            dest_file=tmp_path / "out.enc",
            passphrase="test-key",
        )
        assert result["ok"] is False
        assert "introuvable" in result["error"].lower()

    def test_encrypt_no_passphrase(self, vault, env_file, tmp_path, monkeypatch):
        """Aucune passphrase -> ok=False."""
        monkeypatch.delenv("EZZIO_VAULT_PASSPHRASE", raising=False)
        monkeypatch.delenv("EZZIO_MASTER_KEY", raising=False)
        result = vault.encrypt_env(
            source_file=env_file,
            dest_file=tmp_path / "out.enc",
        )
        assert result["ok"] is False
        assert "clé maître" in result["error"].lower() or "clé" in result["error"].lower()

    def test_encrypt_creates_envelope(self, vault, env_file, tmp_path):
        """encrypt_env crée un fichier envelope JSON."""
        dest = tmp_path / "out.enc"
        result = vault.encrypt_env(
            source_file=env_file,
            dest_file=dest,
            passphrase="test-key-123",
        )
        assert result["ok"] is True
        assert dest.exists()
        assert result["bytes_encrypted"] > 0

        # Vérifier la structure du envelope
        envelope = json.loads(dest.read_text(encoding="utf-8"))
        assert "salt_b64" in envelope
        assert "nonce_b64" in envelope
        assert "data_b64" in envelope
        assert "algorithm" in envelope
        assert envelope["version"] == "2.0"

    def test_round_trip(self, vault, env_file, tmp_path):
        """Round-trip encrypt -> decrypt."""
        dest = tmp_path / "out.enc"
        vault.encrypt_env(env_file, dest, passphrase="test-key-123")
        result = vault.decrypt_to_memory(dest, passphrase="test-key-123")
        assert result["ok"] is True
        assert result["env_vars"]["API_KEY"] == "secret123"
        assert result["env_vars"]["DB_PASSWORD"] == "hunter2"
        assert result["env_vars"]["TOKEN"] == "quoted-value"

    def test_decrypt_wrong_passphrase(self, vault, env_file, tmp_path):
        """Mauvais mot de passe -> ok=False."""
        dest = tmp_path / "out.enc"
        vault.encrypt_env(env_file, dest, passphrase="correct")
        result = vault.decrypt_to_memory(dest, passphrase="wrong")
        assert result["ok"] is False

    def test_decrypt_missing_file(self, vault, tmp_path):
        """Fichier chiffré absent -> ok=False."""
        result = vault.decrypt_to_memory(
            tmp_path / "nope.enc",
            passphrase="test",
        )
        assert result["ok"] is False
        assert "introuvable" in result["error"].lower()

    def test_decrypt_no_passphrase(self, vault, env_file, tmp_path, monkeypatch):
        """Déchiffrement sans passphrase -> ok=False."""
        dest = tmp_path / "out.enc"
        vault.encrypt_env(env_file, dest, passphrase="key")
        monkeypatch.delenv("EZZIO_VAULT_PASSPHRASE", raising=False)
        monkeypatch.delenv("EZZIO_MASTER_KEY", raising=False)
        result = vault.decrypt_to_memory(dest)
        assert result["ok"] is False

    def test_decrypt_corrupted_envelope(self, vault, tmp_path):
        """Envelope corrompu -> ok=False."""
        bad = tmp_path / "bad.enc"
        bad.write_text("NOT JSON {{{", encoding="utf-8")
        result = vault.decrypt_to_memory(bad, passphrase="any")
        assert result["ok"] is False

    def test_encrypt_via_env_var(self, vault, env_file, tmp_path, monkeypatch):
        """Passphrase via variable d'environnement."""
        monkeypatch.setenv("EZZIO_VAULT_PASSPHRASE", "env-pass-456")
        dest = tmp_path / "out.enc"
        result = vault.encrypt_env(env_file, dest)
        assert result["ok"] is True
        assert result["key_source"] == "env"

    def test_empty_env_file(self, vault, tmp_path):
        """Fichier .env vide -> round-trip OK, 0 vars."""
        empty = tmp_path / "empty.env"
        empty.write_text("", encoding="utf-8")
        dest = tmp_path / "out.enc"
        vault.encrypt_env(empty, dest, passphrase="k")
        result = vault.decrypt_to_memory(dest, passphrase="k")
        assert result["ok"] is True
        assert result["keys_count"] == 0
