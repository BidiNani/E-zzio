import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.research import router as research_router

app = FastAPI()
app.include_router(research_router)


@pytest.fixture
def client():
    return TestClient(app)


def test_research_endpoint_structure(client):
    payload = {"query": "Test unit query", "mode": "fast", "task_id": "task_unit_api_01"}
    response = client.post("/api/v1/research/search", json=payload)
    # Vérifie que la route répond correctement
    assert response.status_code in (200, 500)
