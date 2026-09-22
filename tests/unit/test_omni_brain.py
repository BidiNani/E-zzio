"""Tests pour core/omni_brain.py.

Ce module dépend de `ollama` (runtime) et `dotenv`. On teste uniquement
les fonctions pures et les fonctions dont les dépendances sont mockables
(load_config, get_lan_ips). Les fonctions qui nécessitent un environnement
runtime complet (build_system_prompt → CanonicalIdentity fail-closed,
local_brain_reply → ollama serveur, handle_command) sont hors périmètre.

Notes issues du run V3-b3 :
- write_json_event NE crée PAS le dossier parent (l'appelant doit le faire).
- build_system_prompt dépend de runtime/identity/persona.hash (absent en CI).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core import omni_brain

# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def fake_config(monkeypatch):
    """Remplace load_config() par une version retournant un dict contrôlé."""
    config = {
        "EZZIO_BRIDGE_ALLOW_SEND": "false",
        "EZZIO_MOBILE_SHARED_TOKEN": "secret-token-abc123",
        "DISCORD_WEBHOOK_URL": "",
        "DISCORD_BOT_TOKEN": "",
        "META_PAGE_ACCESS_TOKEN": "",
        "META_DEFAULT_RECIPIENT_PSID": "",
    }

    def _fake_load_config():
        return config

    monkeypatch.setattr(omni_brain, "load_config", _fake_load_config)
    return config


# ============================================================
# 1. _bool — parsing booléen (100% pur)
# ============================================================

class TestBool:
    def test_true_variants(self):
        """Toutes les variantes de "true" reconnues."""
        for v in ["1", "true", "TRUE", "True", "yes", "YES", "y", "Y", "on", "ON", " on "]:
            assert omni_brain._bool(v) is True, f"échec sur {v!r}"

    def test_false_variants(self):
        """Tout le reste = False."""
        for v in ["0", "false", "no", "n", "off", "nope", "", "xyz", "2"]:
            assert omni_brain._bool(v) is False, f"échec sur {v!r}"

    def test_none_returns_default(self):
        """None -> default."""
        assert omni_brain._bool(None) is False
        assert omni_brain._bool(None, default=True) is True


# ============================================================
# 2. _redact — masquage de token (100% pur)
# ============================================================

class TestRedact:
    def test_empty(self):
        """Chaîne vide -> chaîne vide."""
        assert omni_brain._redact("") == ""

    def test_none_like(self):
        """None ou falsy -> chaîne vide."""
        assert omni_brain._redact(None) == ""

    def test_short(self):
        """Token court (<=10) -> "***"."""
        assert omni_brain._redact("abc") == "***"
        assert omni_brain._redact("1234567890") == "***"

    def test_long(self):
        """Token long -> 5 premiers + ... + 5 derniers."""
        result = omni_brain._redact("abcdefghijklmnop")
        assert result == "abcde...lmnop"
        assert len(result) == 13


# ============================================================
# 3. verify_mobile_token — comparaison de token
# ============================================================

class TestVerifyMobileToken:
    def test_correct_token(self, fake_config):
        """Token qui correspond -> True."""
        assert omni_brain.verify_mobile_token("secret-token-abc123") is True

    def test_wrong_token(self, fake_config):
        """Mauvais token -> False."""
        assert omni_brain.verify_mobile_token("wrong") is False

    def test_empty_token(self, fake_config):
        """Token vide -> False."""
        assert omni_brain.verify_mobile_token("") is False
        assert omni_brain.verify_mobile_token(None) is False

    def test_no_expected_token(self, monkeypatch):
        """Si la config n'a pas de token -> False même avec un token valide."""
        monkeypatch.setattr(
            omni_brain, "load_config",
            lambda: {"EZZIO_MOBILE_SHARED_TOKEN": ""},
        )
        assert omni_brain.verify_mobile_token("anything") is False


# ============================================================
# 4. integration_truth — état des intégrations
# ============================================================

class TestIntegrationTruth:
    def test_returns_ok(self, fake_config):
        """Retourne un dict avec ok=True."""
        result = omni_brain.integration_truth()
        assert isinstance(result, dict)
        assert result["ok"] is True

    def test_required_sections(self, fake_config):
        """Contient toutes les sections attendues."""
        result = omni_brain.integration_truth()
        for key in ["pc", "smartphone", "discord", "messenger", "ads", "gpu"]:
            assert key in result, f"section manquante : {key}"

    def test_ads_forbidden(self, fake_config):
        """La section ads doit toujours être 'forbidden'."""
        result = omni_brain.integration_truth()
        assert result["ads"]["state"] == "forbidden"

    def test_gpu_untouched(self, fake_config):
        """La section gpu doit toujours être 'untouched'."""
        result = omni_brain.integration_truth()
        assert result["gpu"]["state"] == "untouched"

    def test_discord_not_configured(self, fake_config):
        """Sans webhook ni bot token -> not_configured."""
        result = omni_brain.integration_truth()
        assert result["discord"]["state"] == "ready_not_configured"
        assert result["discord"]["webhook_configured"] is False
        assert result["discord"]["bot_configured"] is False

    def test_discord_configured(self, monkeypatch):
        """Avec webhook -> configured."""
        monkeypatch.setattr(
            omni_brain, "load_config",
            lambda: {
                "DISCORD_WEBHOOK_URL": "https://discord.com/webhook/xxx",
                "DISCORD_BOT_TOKEN": "",
                "EZZIO_BRIDGE_ALLOW_SEND": "false",
            },
        )
        result = omni_brain.integration_truth()
        assert result["discord"]["state"] == "configured"
        assert result["discord"]["webhook_configured"] is True

    def test_messenger_not_configured(self, fake_config):
        """Sans page token -> not_configured."""
        result = omni_brain.integration_truth()
        assert result["messenger"]["state"] == "ready_not_configured"

    def test_send_enabled_true(self, monkeypatch):
        """EZZIO_BRIDGE_ALLOW_SEND=true -> send_enabled=True."""
        monkeypatch.setattr(
            omni_brain, "load_config",
            lambda: {
                "EZZIO_BRIDGE_ALLOW_SEND": "true",
                "DISCORD_WEBHOOK_URL": "",
                "DISCORD_BOT_TOKEN": "",
                "META_PAGE_ACCESS_TOKEN": "",
            },
        )
        result = omni_brain.integration_truth()
        assert result["discord"]["send_enabled"] is True
        assert result["messenger"]["send_enabled"] is True


# ============================================================
# 5. mobile_config — config mobile
# ============================================================

class TestMobileConfig:
    def test_returns_ok(self, fake_config, monkeypatch):
        """Retourne ok=True même sans IPs."""
        monkeypatch.setattr(omni_brain, "get_lan_ips", lambda: [])
        result = omni_brain.mobile_config()
        assert result["ok"] is True

    def test_token_is_redacted(self, fake_config, monkeypatch):
        """Le token n'apparaît jamais en clair dans la config."""
        monkeypatch.setattr(omni_brain, "get_lan_ips", lambda: [])
        result = omni_brain.mobile_config()
        assert "secret-token-abc123" not in json.dumps(result)

    def test_urls_generated_for_ips(self, fake_config, monkeypatch):
        """Une entrée URLs par IP LAN détectée."""
        monkeypatch.setattr(omni_brain, "get_lan_ips", lambda: ["192.168.1.10", "10.0.0.5"])
        result = omni_brain.mobile_config()
        assert len(result["urls"]) == 2
        assert result["urls"][0]["host"] == "192.168.1.10"
        assert "192.168.1.10:8001" in result["urls"][0]["base_url"]

    def test_policy_is_strict(self, fake_config, monkeypatch):
        """La policy interdit pub/tracking/GPU."""
        monkeypatch.setattr(omni_brain, "get_lan_ips", lambda: [])
        result = omni_brain.mobile_config()
        policy = result["policy"]
        assert policy["local_wifi_only"] is True
        assert policy["ads"] == "forbidden"
        assert policy["tracking"] == "forbidden"
        assert policy["gpu"] == "untouched"


# ============================================================
# 6. write_json_event — écriture d'événements
# ============================================================

class TestWriteJsonEvent:
    def test_creates_file(self, tmp_path):
        """write_json_event écrit un fichier dans un dossier existant."""
        folder = tmp_path / "events"
        folder.mkdir()
        omni_brain.write_json_event(folder, "test_kind", {"data": "x"})
        files = list(folder.glob("*.json"))
        assert len(files) >= 1

    def test_file_content(self, tmp_path):
        """Le fichier contient l'id, le kind et le payload."""
        folder = tmp_path / "events2"
        folder.mkdir()
        omni_brain.write_json_event(folder, "my_kind", {"foo": "bar"})
        files = list(folder.glob("*.json"))
        assert len(files) >= 1
        content = json.loads(files[0].read_text(encoding="utf-8"))
        assert content.get("kind") == "my_kind"
        assert (
            content.get("payload") == {"foo": "bar"}
            or content.get("data") == {"foo": "bar"}
        )
        assert "id" in content

    def test_missing_folder_raises(self, tmp_path):
        """write_json_event ne crée PAS le dossier (comportement documenté).

        L'appelant doit s'assurer que le dossier existe.
        """
        missing = tmp_path / "does_not_exist"
        with pytest.raises(FileNotFoundError):
            omni_brain.write_json_event(missing, "test", {})


# ============================================================
# 7. Smoke tests
# ============================================================

class TestSmoke:
    def test_module_imports(self):
        """Le module s'importe (ollama est requis)."""
        assert omni_brain is not None

    def test_available_commands(self):
        """available_commands() retourne un dict avec 'commands'."""
        result = omni_brain.available_commands()
        assert isinstance(result, dict)
        assert "commands" in result
        assert isinstance(result["commands"], list)

    def test_sanitize_reply(self):
        """sanitize_reply ne crashe pas sur des entrées simples."""
        assert isinstance(omni_brain.sanitize_reply(""), str)
        assert isinstance(omni_brain.sanitize_reply("Hello world"), str)

    def test_bridge_status_returns_dict(self):
        """bridge_status() retourne un dict."""
        result = omni_brain.bridge_status()
        assert isinstance(result, dict)
