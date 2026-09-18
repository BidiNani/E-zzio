"""
Test de conformité de l'invariant d'indépendance de démarrage :
Prouve que web_server.py démarre et reste accessible même si Ollama est complètement OFFLINE.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from core.models.provider_health import probe_ollama_status
from web_server import app


@pytest.mark.asyncio
async def test_web_server_startup_independent_of_ollama_offline():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1:8001") as client:
        # 1. /health reste ONLINE même si un provider est éteint
        r_health = await client.get("/health")
        assert r_health.status_code == 200
        assert r_health.json()["status"] == "ONLINE"

        # 2. /metrics rapporte fidèlement l'état de capacité du provider sans crasher
        r_metrics = await client.get("/metrics")
        assert r_metrics.status_code == 200
        metrics = r_metrics.json()
        assert "providers_health" in metrics
        assert metrics["providers_health"]["ollama_local"] in ["ONLINE", "OFFLINE"]

        # 3. La perception reste opérationnelle
        r_perc = await client.get("/perception/status")
        assert r_perc.status_code == 200
        assert r_perc.json()["ok"] is True
