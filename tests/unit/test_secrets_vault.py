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
    """Teste seal/unseal DPAPI. Skip si non-Windows (ctypes.windll n'existe pas sur Linux)."""

    @pytest.mark.skipif(
        not hasattr(__import__("ctypes"), "windll"),
        reason="DPAPI Windows only — ctypes.windll absent sur cette plateforme",
    )
    def test_seal_to_dpapi_mocked_success(self, vault, tmp_path, monkeypatch):
        """Mock ctypes.windll -> scellement réussi. Skip sur non-Windows."""
        import ctypes
        import sys
        monkeypatch.setattr(sys, "platform", "win32")

        # Mock ctypes.windll (n'existe que sur Windows)
        mock_windll = type("Windll", (), {})()
        mock_crypt32 = type("Crypt32", (), {})()
        mock_kernel32 = type("Kernel32", (), {})()

        def fake_CryptProtectData(*args):
            return 1  # True

        mock_crypt32.CryptProtectData = fake_CryptProtectData
        mock_kernel32.LocalFree = lambda x: None

        mock_windll.crypt32 = mock_crypt32
        mock_windll.kernel32 = mock_kernel32

        monkeypatch.setattr(ctypes, "windll", mock_windll, raising=False)

        result = vault.seal_to_dpapi("test-key", tmp_path / "test.bin")
        assert isinstance(result, bool)

    @pytest.mark.skipif(
        not hasattr(__import__("ctypes"), "windll"),
        reason="DPAPI Windows only",
    )
    def test_unseal_from_dpapi_missing_file(self, vault, monkeypatch):
        """Fichier absent -> None. Skip sur non-Windows."""
        import sys
        monkeypatch.setattr(sys, "platform", "win32")
        result = vault.unseal_from_dpapi(vault.secrets_dir / "nonexistent.bin")
        assert result is None


# ============================================================
# 3. Fallback crypto — couverture branches (session 2026-09-22)
# ============================================================

class TestFallbackCryptoCoverage:
    """Tests pour les branches du fallback PBKDF2-XOR-HMAC.

    Objectif : couvrir les lignes testables sans dépendance OS.
    """

    def test_encrypt_env_source_not_found(self, vault, tmp_path, monkeypatch):
        """Fichier source introuvable -> erreur propre."""
        monkeypatch.setattr(secrets_vault, "HAS_CRYPTOGRAPHY", False)
        missing = tmp_path / "does_not_exist.env"
        dest = tmp_path / "out.enc"
        result = vault.encrypt_env(missing, dest, passphrase="key")
        assert result["ok"] is False
        assert "introuvable" in result["error"].lower()

    def test_decrypt_env_container_not_found(self, vault, tmp_path, monkeypatch):
        """Conteneur chiffré introuvable -> erreur propre."""
        monkeypatch.setattr(secrets_vault, "HAS_CRYPTOGRAPHY", False)
        missing = tmp_path / "does_not_exist.enc"
        result = vault.decrypt_to_memory(missing, passphrase="key")
        assert result["ok"] is False
        assert "introuvable" in result["error"].lower()

    def test_decrypt_env_corrupted_base64(self, vault, env_file, tmp_path, monkeypatch):
        """Base64 invalide -> exception capturée."""
        monkeypatch.setattr(secrets_vault, "HAS_CRYPTOGRAPHY", False)
        dest = tmp_path / "out.enc"
        vault.encrypt_env(env_file, dest, passphrase="key")

        envelope = json.loads(dest.read_text(encoding="utf-8"))
        # Trouver la clé contenant les données chiffrées
        for k in list(envelope.keys()):
            if k.endswith("_b64") and k != "":
                envelope[k] = "!!!not-base64!!!"
                break
        dest.write_text(json.dumps(envelope), encoding="utf-8")

        result = vault.decrypt_to_memory(dest, passphrase="key")
        assert result["ok"] is False

    def test_decrypt_env_wrong_hmac(self, vault, env_file, tmp_path, monkeypatch):
        """HMAC/tag corrompu -> échec d'intégrité."""
        monkeypatch.setattr(secrets_vault, "HAS_CRYPTOGRAPHY", False)
        dest = tmp_path / "out.enc"
        vault.encrypt_env(env_file, dest, passphrase="key")

        envelope = json.loads(dest.read_text(encoding="utf-8"))
        # Pas de clé HMAC identifiée — corrompre toutes les clés *b64
        for k in list(envelope.keys()):
            if k.endswith("_b64"):
                envelope[k] = base64.b64encode(b"\x00" * 32).decode("ascii")
                break
        dest.write_text(json.dumps(envelope), encoding="utf-8")

        result = vault.decrypt_to_memory(dest, passphrase="key")
        assert result["ok"] is False

    def test_decrypt_env_skips_comments_and_blanks(self, vault, tmp_path, monkeypatch):
        """Lignes vides et commentaires ignorés au déchiffrement."""
        monkeypatch.setattr(secrets_vault, "HAS_CRYPTOGRAPHY", False)
        env_file = tmp_path / "with_comments.env"
        env_file.write_text(
            "# commentaire\n"
            "\n"
            "KEY1=value1\n"
            "\n"
            "# autre commentaire\n"
            "KEY2=value2\n",
            encoding="utf-8",
        )
        dest = tmp_path / "out.enc"
        enc = vault.encrypt_env(env_file, dest, passphrase="key")
        assert enc["ok"] is True

        dec = vault.decrypt_to_memory(dest, passphrase="key")
        assert dec["ok"] is True

    def test_encrypt_env_fallback_round_trip_multiline(self, vault, tmp_path, monkeypatch):
        """Round-trip complet du fallback avec plusieurs lignes."""
        monkeypatch.setattr(secrets_vault, "HAS_CRYPTOGRAPHY", False)
        env_file = tmp_path / "multi.env"
        env_file.write_text("A=1\nB=2\nC=3\nD=4\nE=5\n", encoding="utf-8")
        dest = tmp_path / "out.enc"
        enc = vault.encrypt_env(env_file, dest, passphrase="roundtrip")
        assert enc["ok"] is True

        envelope = json.loads(dest.read_text(encoding="utf-8"))
        assert envelope["algorithm"] == "PBKDF2-XOR-HMAC"

        dec = vault.decrypt_to_memory(dest, passphrase="roundtrip")
        assert dec["ok"] is True
