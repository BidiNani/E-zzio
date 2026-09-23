"""Tests pour core/models/provider_health.py."""
from __future__ import annotations

from unittest.mock import patch

from core.models.provider_health import (
    _CACHE_TTL_SEC,
    _ollama_status_cache,
    get_providers_health,
    probe_ollama_status,
)


class TestProbeOllamaStatus:
    def setup_method(self):
        # Reset cache avant chaque test
        _ollama_status_cache["status"] = "OFFLINE"
        _ollama_status_cache["timestamp"] = 0.0

    def test_online_when_socket_connects(self):
        with patch("core.models.provider_health.socket.create_connection"):
            result = probe_ollama_status(force_refresh=True)
            assert result == "ONLINE"

    def test_offline_on_timeout(self):
        with patch("core.models.provider_health.socket.create_connection",
                   side_effect=TimeoutError("timeout")):
            result = probe_ollama_status(force_refresh=True)
            assert result == "OFFLINE"

    def test_offline_on_oserror(self):
        with patch("core.models.provider_health.socket.create_connection",
                   side_effect=OSError("refused")):
            result = probe_ollama_status(force_refresh=True)
            assert result == "OFFLINE"

    def test_cache_returns_without_probe(self):
        import time
        _ollama_status_cache["status"] = "ONLINE"
        _ollama_status_cache["timestamp"] = time.time()
        # Ne devrait PAS appeler socket
        with patch("core.models.provider_health.socket.create_connection") as mock_sock:
            result = probe_ollama_status(force_refresh=False)
            assert result == "ONLINE"
            mock_sock.assert_not_called()


class TestGetProvidersHealth:
    def test_returns_dict_with_expected_keys(self):
        with patch("core.models.provider_health.probe_ollama_status", return_value="ONLINE"):
            result = get_providers_health()
            assert result["gemini"] == "ONLINE"
            assert result["ollama_local"] == "ONLINE"

