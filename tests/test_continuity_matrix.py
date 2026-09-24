"""tests/test_continuity_matrix.py — Matrix de continuité et de tolérance aux pannes simulées E-ZZIO.

Mesure de la tolérance aux pannes (Gemini DOWN, Groq DOWN, Ollama DOWN, 429, Timeout,
Internet OFF, Total Provider Loss, Non-corruption, et Recovery).
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.agent.agent_provider import AgentProviderAdapter
from core.cognition.cognitive_gateway import CognitiveGateway
from core.cognition.model_router import ModelRouter
from core.ezzio_master import EzzioMaster
from core.kernel.native_harness import HarnessState, NativeHarness
from core.providers.base_provider import ProviderResponse
from core.providers.registry import ProviderFactory


class InMemoryGateway:
    """Passerelle mémoire simulée pour tests isolés sans I/O disque."""
    def __init__(self):
        self.sessions = {}

    async def init(self):
        pass

    async def record_message(self, session_id: str, role: str, content: str, metadata=None):
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append({"role": role, "content": content, "metadata": metadata or {}})

    async def get_session_history(self, session_id: str, limit: int = 10):
        return self.sessions.get(session_id, [])[-limit:]

    async def search_memory(self, query: str, limit: int = 2):
        return {"chat_history": []}


# ------------------------------------------------------------
# SCÉNARIO 1 : EXECUTION NORMALE (CONTINUOUS)
# ------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_1_normal_execution(monkeypatch):
    """SCÉNARIO 1: Execution normale quand le provider est disponible -> CONTINUOUS."""
    def mock_create(name: str, **kwargs):
        fake_prov = AsyncMock()
        fake_prov.generate = AsyncMock(return_value=ProviderResponse(
            content="Reponse normale", model="gemini-3.7-flash", provider="gemini"
        ))
        return fake_prov

    monkeypatch.setattr(ProviderFactory, "create", mock_create)

    master = EzzioMaster()
    master.memory = InMemoryGateway()
    master._memory_initialized = True

    res = await master.execute_intent("Question normale", session_id="sess-sc1")

    assert res["ok"] is True
    assert res["used_fallback"] is False
    assert res["provider"] == "gemini"
    assert res["response"] == "Reponse normale"


# ------------------------------------------------------------
# SCÉNARIO 2 : GEMINI DOWN -> FALLBACK (DEGRADED)
# ------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_2_gemini_down_fallback(monkeypatch):
    """SCÉNARIO 2: Gemini DOWN -> bascule sur le fallback canonique (Groq/Lite) -> DEGRADED."""
    calls = []

    def mock_create(name: str, **kwargs):
        calls.append(name)
        fake_prov = AsyncMock()
        if len(calls) == 1:
            # Gemini panique
            fake_prov.generate = AsyncMock(side_effect=RuntimeError("503 Service Unavailable: Gemini API Down"))
        else:
            # Fallback reussit
            fake_prov.generate = AsyncMock(return_value=ProviderResponse(
                content="Reponse via fallback Groq", model="llama-3.3-70b-versatile", provider="groq"
            ))
        return fake_prov

    monkeypatch.setattr(ProviderFactory, "create", mock_create)

    master = EzzioMaster()
    master.memory = InMemoryGateway()
    master._memory_initialized = True

    res = await master.execute_intent("Prompt Gemini Down", session_id="sess-sc2")

    assert res["ok"] is True
    assert res["used_fallback"] is True
    assert res["fallback_notice"] is not None
    assert "Reponse via fallback Groq" in res["response"]


# ------------------------------------------------------------
# SCÉNARIO 3 : GROQ DOWN -> FALLBACK (DEGRADED)
# ------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_3_groq_down_fallback(monkeypatch):
    """SCÉNARIO 3: Groq DOWN -> bascule sur le fallback canonique -> DEGRADED."""
    calls = []

    def mock_create(name: str, **kwargs):
        calls.append(name)
        fake_prov = AsyncMock()
        if len(calls) == 1:
            fake_prov.generate = AsyncMock(side_effect=TimeoutError("Groq endpoint timeout"))
        else:
            fake_prov.generate = AsyncMock(return_value=ProviderResponse(
                content="Reponse via fallback Gemini", model="gemini-3.5-flash-lite", provider="gemini"
            ))
        return fake_prov

    monkeypatch.setattr(ProviderFactory, "create", mock_create)

    master = EzzioMaster()
    master.memory = InMemoryGateway()
    master._memory_initialized = True

    res = await master.execute_intent("Prompt Groq Down", session_id="sess-sc3")

    assert res["ok"] is True
    assert res["used_fallback"] is True


# ------------------------------------------------------------
# SCÉNARIO 4 : OLLAMA DOWN -> CLOUD FALLBACK (DEGRADED)
# ------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_4_ollama_down_fallback(monkeypatch):
    """SCÉNARIO 4: Ollama local DOWN -> bascule vers le provider cloud -> DEGRADED."""
    calls = []

    def mock_create(name: str, **kwargs):
        calls.append(name)
        fake_prov = AsyncMock()
        if name == "ollama":
            fake_prov.generate = AsyncMock(side_effect=ConnectionError("Ollama daemon 127.0.0.1:11434 unreachable"))
        else:
            fake_prov.generate = AsyncMock(return_value=ProviderResponse(
                content="Reponse cloud de secours", model="gemini-3.7-flash", provider="gemini"
            ))
        return fake_prov

    monkeypatch.setattr(ProviderFactory, "create", mock_create)

    master = EzzioMaster()
    master.memory = InMemoryGateway()
    master._memory_initialized = True

    res = await master.execute_intent("Prompt Ollama Down", model_target="local", session_id="sess-sc4")

    assert res["ok"] is True
    assert res["used_fallback"] is True
    assert "Reponse cloud de secours" in res["response"]


# ------------------------------------------------------------
# SCÉNARIO 5 : CLOUD DOWN -> LOCAL FALLBACK (DEGRADED)
# ------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_5_cloud_down_local_fallback(monkeypatch):
    """SCÉNARIO 5: Providers cloud DOWN -> bascule sur le provider local si disponible -> DEGRADED."""
    def mock_create(name: str, **kwargs):
        fake_prov = AsyncMock()
        if name in ["gemini", "groq"]:
            fake_prov.generate = AsyncMock(side_effect=ConnectionError("Cloud APIs unreachable"))
        else:
            fake_prov.generate = AsyncMock(return_value=ProviderResponse(
                content="Reponse locale Ollama Qwen", model="qwen2.5-coder:7b-instruct-q4_K_M", provider="ollama"
            ))
        return fake_prov

    monkeypatch.setattr(ProviderFactory, "create", mock_create)

    # Forcer fallback vers ollama
    monkeypatch.setattr("routers.settings.FALLBACK_MAP", {"gemini": "qwen2.5-coder:7b-instruct-q4_K_M"})

    master = EzzioMaster()
    master.memory = InMemoryGateway()
    master._memory_initialized = True

    res = await master.execute_intent("Prompt Cloud Down", session_id="sess-sc5")

    assert res["ok"] is True
    assert res["used_fallback"] is True


# ------------------------------------------------------------
# SCÉNARIO 6 : INTERNET OFFLINE SIMULÉ (DEGRADED)
# ------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_6_internet_offline_simulated(monkeypatch):
    """SCÉNARIO 6: Internet coupe -> Erreur reseau simulee -> Bascule locale propre -> DEGRADED."""
    def mock_create(name: str, **kwargs):
        fake_prov = AsyncMock()
        if name != "ollama":
            fake_prov.generate = AsyncMock(side_effect=OSError("Network is unreachable / No DNS"))
        else:
            fake_prov.generate = AsyncMock(return_value=ProviderResponse(
                content="Mode local autonome actif", model="qwen2.5-coder:7b-instruct-q4_K_M", provider="ollama"
            ))
        return fake_prov

    monkeypatch.setattr(ProviderFactory, "create", mock_create)
    monkeypatch.setattr("routers.settings.FALLBACK_MAP", {"gemini": "qwen2.5-coder:7b-instruct-q4_K_M"})

    master = EzzioMaster()
    master.memory = InMemoryGateway()
    master._memory_initialized = True

    res = await master.execute_intent("Prompt Offline", session_id="sess-sc6")

    assert res["ok"] is True
    assert res["used_fallback"] is True
    assert "Mode local autonome" in res["response"]


# ------------------------------------------------------------
# SCÉNARIO 7 : QUOTA / RATE LIMIT (429) (DEGRADED)
# ------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_7_rate_limit_429(monkeypatch):
    """SCÉNARIO 7: Erreur HTTP 429 / Quota d'un provider -> Fallback execute proprement -> DEGRADED."""
    calls = []

    def mock_create(name: str, **kwargs):
        calls.append(name)
        fake_prov = AsyncMock()
        if len(calls) == 1:
            fake_prov.generate = AsyncMock(side_effect=RuntimeError("429 Too Many Requests: Quota exhausted"))
        else:
            fake_prov.generate = AsyncMock(return_value=ProviderResponse(
                content="Reponse post-429 via fallback", model="gemini-3.5-flash-lite", provider="gemini"
            ))
        return fake_prov

    monkeypatch.setattr(ProviderFactory, "create", mock_create)

    master = EzzioMaster()
    master.memory = InMemoryGateway()
    master._memory_initialized = True

    res = await master.execute_intent("Prompt Rate Limit", session_id="sess-sc7")

    assert res["ok"] is True
    assert res["used_fallback"] is True


# ------------------------------------------------------------
# SCÉNARIO 8 : TIMEOUT / 5XX ERROR (DEGRADED)
# ------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_8_timeout_5xx(monkeypatch):
    """SCÉNARIO 8: Timeout ou 500 Internal Server Error -> Fallback -> DEGRADED."""
    calls = []

    def mock_create(name: str, **kwargs):
        calls.append(name)
        fake_prov = AsyncMock()
        if len(calls) == 1:
            fake_prov.generate = AsyncMock(side_effect=TimeoutError("Timeout after 30s"))
        else:
            fake_prov.generate = AsyncMock(return_value=ProviderResponse(
                content="Reponse post-timeout via fallback", model="gemini-3.5-flash-lite", provider="gemini"
            ))
        return fake_prov

    monkeypatch.setattr(ProviderFactory, "create", mock_create)

    master = EzzioMaster()
    master.memory = InMemoryGateway()
    master._memory_initialized = True

    res = await master.execute_intent("Prompt Timeout", session_id="sess-sc8")

    assert res["ok"] is True
    assert res["used_fallback"] is True


# ------------------------------------------------------------
# SCÉNARIO 9 : TOUS PROVIDERS DOWN (FAIL-CLOSED)
# ------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_9_all_providers_down_fail_closed(monkeypatch):
    """SCÉNARIO 9: Tous les providers LLM sont DOWN -> Rejet propre Fail-Closed sans crash ni corruption -> FAIL-CLOSED."""
    def mock_create(name: str, **kwargs):
        fake_prov = AsyncMock()
        fake_prov.generate = AsyncMock(side_effect=RuntimeError("500 Server Error: Provider Dead"))
        return fake_prov

    monkeypatch.setattr(ProviderFactory, "create", mock_create)

    master = EzzioMaster()
    mem = InMemoryGateway()
    master.memory = mem
    master._memory_initialized = True

    res = await master.execute_intent("Prompt Fail Closed", session_id="sess-sc9")

    # NativeHarness capture l'erreur et renvoie un resultat propre status=FAILED
    assert res["ok"] is False
    assert "[FAIL-CLOSED]" in res["response"]

    # Verification non-corruption : la memoire enregistre le message fail-closed de maniere coherente
    hist = await mem.get_session_history("sess-sc9")
    assert len(hist) > 0
    assert "[FAIL-CLOSED]" in hist[-1]["content"]


# ------------------------------------------------------------
# SCÉNARIO 10 : RECOVERY & ISOLATION MULTI-MISSION (CONTINUOUS)
# ------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_10_recovery_and_isolation(monkeypatch):
    """SCÉNARIO 10: Mission 1 subit une panne, Mission 2 apres retablissement du provider reussit normalement -> CONTINUOUS."""
    provider_status = {"gemini_ok": False}

    def mock_create(name: str, **kwargs):
        fake_prov = AsyncMock()
        async def fake_gen(*args, **gen_kwargs):
            if not provider_status["gemini_ok"]:
                raise RuntimeError("Gemini Down Temporarily")
            return ProviderResponse(content="Reponse retablie Gemini", model="gemini-3.7-flash", provider="gemini")
        fake_prov.generate = fake_gen
        return fake_prov

    monkeypatch.setattr(ProviderFactory, "create", mock_create)

    master = EzzioMaster()
    mem = InMemoryGateway()
    master.memory = mem
    master._memory_initialized = True

    # Tour 1 : Gemini DOWN -> Bascule ou fail
    res1 = await master.execute_intent("Mission 1 - Down", session_id="sess-sc10")
    assert res1["used_fallback"] is True or res1["ok"] is False

    # Retablissement du provider Gemini
    provider_status["gemini_ok"] = True

    # Tour 2 : Gemini OK -> Mission 2 executee normalement sans residu de panne
    res2 = await master.execute_intent("Mission 2 - Restored", session_id="sess-sc10")
    assert res2["ok"] is True
    assert res2["used_fallback"] is False
    assert res2["response"] == "Reponse retablie Gemini"


# ------------------------------------------------------------
# SCÉNARIO 11 : SURVIE DU CORE DÉTERMINISTE (CAPABILITY A)
# ------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_11_deterministic_core_survival():
    """SCÉNARIO 11: Les fonctions d'analyse, d'audit, de policy guard et de transition FSM fonctionnent sans dépendance LLM dans ce scénario déterministe."""
    harness = NativeHarness()

    # Sanitization et Policy Guard fonctionnent sans reseau ni LLM
    sanitized = harness.sanitize_error(Exception("Secret API key AIzaSyTestKey inside error"), "corr-11")
    assert "AIzaSy" not in sanitized["safe_message"]
    assert "[REDACTED SECURITY EXCEPTION]" in sanitized["safe_message"]

    # FSM NativeHarness fonctionne sans LLM
    res = await harness.execute_task(
        task_prompt="Audit de conformite de securite",
        session_id="sess-sc11",
        executor=None  # Aucun executor LLM
    )
    assert res["status"] == "SUCCESS"
    assert res["turn"] == 1
