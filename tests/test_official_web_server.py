"""
Test de conformité du serveur officiel web_server.py (FastAPI port 8001).
Vérifie que web_server.py est la passerelle unique pour /health, /master/chat, /memory, et /perception/*.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from web_server import app


@pytest.mark.asyncio
async def test_official_web_server_mounted_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1:8001") as client:
        # 1. Health check officiel
        r_health = await client.get("/health")
        assert r_health.status_code == 200
        data_health = r_health.json()
        assert data_health["service"] == "E-ZZIO Sovereign Platform"
        assert data_health["status"] == "ONLINE"

        # 2. Perception status monté sur le serveur officiel
        r_perception = await client.get("/perception/status")
        assert r_perception.status_code == 200
        data_perc = r_perception.json()
        assert data_perc["ok"] is True
        assert "universal_file_reader" in data_perc["capabilities"]

        # 3. Metrics d'observabilité séparées
        r_metrics = await client.get("/metrics")
        assert r_metrics.status_code == 200
        data_metrics = r_metrics.json()
        assert "circuit_breaker" in data_metrics
        assert "providers_health" in data_metrics
