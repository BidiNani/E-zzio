import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from v17.api.router import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_v17_3_ui_security_no_secrets_in_template():
    res = client.get("/api/v17/product/ui")
    content = res.text
    assert "DISCORD_TOKEN=" not in content
    assert "GEMINI_API_KEY=" not in content
    assert "GROQ_API_KEY=" not in content
    assert "TAVILY_API_KEY=" not in content
    assert "sk-" not in content
