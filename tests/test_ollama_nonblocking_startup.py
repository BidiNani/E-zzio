"""
E-ZZIO V9.0 — OLLAMA NON-BLOCKING STARTUP INVARIANT TEST
Vérifie qu'E-ZZIO démarre et répond avec succès même quand Ollama est indisponible.
"""

import pytest
from unittest.mock import patch
from core.models.provider_health import probe_ollama_status, get_providers_health


def test_ollama_failure_does_not_block_health():
    """Vérifie que probe_ollama_status gère l'indisponibilité d'Ollama sans lever d'exception."""
    with patch("socket.create_connection", side_effect=OSError("Connection refused")):
        status = probe_ollama_status(force_refresh=True)
        assert status == "OFFLINE"

        health = get_providers_health()
        assert health["gemini"] == "ONLINE"
        assert health["ollama_local"] == "OFFLINE"
