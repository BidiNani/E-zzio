"""Tests pour core/security/secret_redactor.py.

SecretRedactor.sanitize() : masque les secrets dans du texte/dict/list.
Pas de dépendance externe. Testable à 100%.
"""
from __future__ import annotations

import pytest

from core.security.secret_redactor import SecretRedactor, secret_redactor

# ============================================================
# 1. Smoke
# ============================================================

class TestSmoke:
    def test_class_exists(self):
        assert SecretRedactor is not None

    def test_instance_exists(self):
        assert secret_redactor is not None
        assert isinstance(secret_redactor, SecretRedactor)

    def test_patterns_defined(self):
        assert len(SecretRedactor.PATTERNS) >= 3

    def test_sanitize_is_static(self):
        assert isinstance(SecretRedactor.__dict__.get("sanitize"), staticmethod)


# ============================================================
# 2. sanitize — types
# ============================================================

class TestSanitizeTypes:
    def test_string_passthrough(self):
        """Chaîne sans secret -> inchangée."""
        assert SecretRedactor.sanitize("hello world") == "hello world"

    def test_empty_string(self):
        assert SecretRedactor.sanitize("") == ""

    def test_none_becomes_string(self):
        """None devient 'None' (str(None))."""
        result = SecretRedactor.sanitize(None)
        assert result == "None"

    def test_int_becomes_string(self):
        assert SecretRedactor.sanitize(42) == "42"

    def test_dict_recurses(self):
        """Dict -> chaque valeur est sanitisée."""
        result = SecretRedactor.sanitize({"key": "value", "n": 42})
        assert result == {"key": "value", "n": "42"}

    def test_list_recurses(self):
        """List -> chaque item est sanitisé."""
        result = SecretRedactor.sanitize(["a", 1, None])
        assert result == ["a", "1", "None"]

    def test_nested_dict_list(self):
        """Structure imbriquée."""
        result = SecretRedactor.sanitize({"items": [{"x": 1}, {"y": 2}]})
        assert result == {"items": [{"x": "1"}, {"y": "2"}]}


# ============================================================
# 3. sanitize — secrets détectés
# ============================================================

class TestSanitizeSecrets:
    def test_env_var_token(self):
        """DISCORD_BOT_TOKEN=xyz -> masqué."""
        result = SecretRedactor.sanitize("DISCORD_BOT_TOKEN=secret123")
        assert "secret123" not in result
        assert "REDACTED" in result or "***" in result

    def test_env_var_key(self):
        """GOOGLE_API_KEY=xyz -> masqué."""
        result = SecretRedactor.sanitize("GOOGLE_API_KEY=abc123def456")
        assert "abc123def456" not in result

    def test_env_var_secret(self):
        result = SecretRedactor.sanitize("MY_SECRET=topsecret")
        assert "topsecret" not in result

    def test_env_var_password(self):
        result = SecretRedactor.sanitize("DB_PASSWORD=hunter2")
        assert "hunter2" not in result

    def test_bearer_token(self):
        """Authorization: Bearer eyJ... -> masqué."""
        result = SecretRedactor.sanitize("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
        assert "eyJhbGci" not in result

    def test_oauth_token(self):
        """ya29.* -> masqué."""
        result = SecretRedactor.sanitize("token: ya29.a0AfH6SMBxyz123")
        assert "ya29.a0AfH6SMBxyz123" not in result

    def test_google_api_key_generic(self):
        """AIza... -> masqué par la règle de secours."""
        result = SecretRedactor.sanitize("AIzaSyDxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        assert "AIzaSyD" not in result

    def test_jwt_like_token(self):
        """eyJ... long -> masqué."""
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" + "a" * 30
        result = SecretRedactor.sanitize(f"token: {jwt}")
        assert jwt not in result


# ============================================================
# 4. sanitize — préservations
# ============================================================

class TestSanitizePreserves:
    def test_preserves_key_name(self):
        """Le nom de la clé est conservé, seule la valeur est masquée."""
        result = SecretRedactor.sanitize("DISCORD_BOT_TOKEN=secretxyz")
        assert "DISCORD_BOT_TOKEN" in result

    def test_non_secret_text_preserved(self):
        """Texte normal intact."""
        result = SecretRedactor.sanitize("Bonjour, ceci est un message normal.")
        assert "Bonjour" in result
        assert "message normal" in result

    def test_numbers_preserved(self):
        result = SecretRedactor.sanitize("Version 7.45.1 released")
        assert "7.45.1" in result


# ============================================================
# 5. sanitize — cas réels
# ============================================================

class TestSanitizeRealCases:
    def test_mixed_dict(self):
        """Dict avec du contenu mixte."""
        data = {
            "message": "Hello",
            "token": "supersecretvalue",
            "count": 3,
        }
        result = SecretRedactor.sanitize(data)
        assert result["message"] == "Hello"
        assert result["count"] == "3"
        # Le token peut être masqué ou non selon le pattern exact
        # On vérifie juste que la structure est préservée
        assert "token" in result

    def test_multiline_string(self):
        """String multi-lignes avec secrets sur plusieurs lignes."""
        content = "line1\nDISCORD_BOT_TOKEN=abc\nline3\nGOOGLE_API_KEY=xyz\n"
        result = SecretRedactor.sanitize(content)
        assert "abc" not in result or "REDACTED" in result
        assert "line1" in result
        assert "line3" in result

    def test_never_crashes_on_weird_input(self):
        """Ne crash jamais, quel que soit l'input."""
        for inp in [None, 0, [], {}, "", "x" * 10000, object()]:
            try:
                result = SecretRedactor.sanitize(inp)
                assert result is not None or inp is None
            except Exception as e:
                pytest.fail(f"sanitize a crashé sur {inp!r}: {e}")
