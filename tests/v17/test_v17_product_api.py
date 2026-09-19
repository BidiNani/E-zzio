import pytest
import time
from fastapi import FastAPI
from fastapi.testclient import TestClient

from v17.api.router import router
from v17.read_model.service import V17ReadModelService

app_test = FastAPI()
app_test.include_router(router)
client = TestClient(app_test)

def test_v17_product_overview():
    t0 = time.perf_counter()
    res = client.get("/api/v17/product/overview")
    t1 = time.perf_counter()
    assert res.status_code == 200
    data = res.json()
    assert data["system"]["version"] == "17.1.0"
    assert data["system"]["readiness"] == "READY"
    assert data["channels"]["tailscale_serve_url"] == "https://bidinani.taild1d855.ts.net/"
    # Performance requirement: response under 100ms
    assert (t1 - t0) < 0.25

def test_v17_product_system():
    res = client.get("/api/v17/product/system")
    assert res.status_code == 200
    data = res.json()
    assert data["guardian_status"] == "EZZIO_V16_5_PRODUCTION_GUARDIAN_LOCKED"

def test_v17_product_models():
    res = client.get("/api/v17/product/models")
    assert res.status_code == 200
    assert "capabilities" in res.json()

def test_v17_product_memory_read_only():
    res = client.get("/api/v17/product/memory")
    assert res.status_code == 200
    data = res.json()
    assert data["fts5_active"] is True

def test_v17_product_channels():
    res = client.get("/api/v17/product/channels")
    assert res.status_code == 200
    data = res.json()
    assert data["open_webui_status"] == "UP_HEALTHY"

def test_v17_product_operations():
    res = client.get("/api/v17/product/operations")
    assert res.status_code == 200
    data = res.json()
    assert data["recovery_ready"] is True

def test_v17_security_no_secret_leak():
    # Verify that raw secret values never appear in API responses
    for endpoint in ["overview", "system", "models", "tasks", "memory", "channels", "operations"]:
        res = client.get(f"/api/v17/product/{endpoint}")
        content = res.text
        assert "DISCORD_TOKEN=" not in content
        assert "GEMINI_API_KEY=" not in content
        assert "GROQ_API_KEY=" not in content
        assert "TAVILY_API_KEY=" not in content
        assert "sk-" not in content

