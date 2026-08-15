import pytest
import asyncio
from core.providers.igoogle_provider import IGoogleProvider
from core.providers.google_drive_provider import GoogleDriveProvider
from core.providers.google_gmail_provider import GoogleGmailProvider
from core.providers.google_calendar_provider import GoogleCalendarProvider
from core.providers.google_docs_provider import GoogleDocsProvider
from core.evidence_store import EvidenceStore

@pytest.mark.asyncio
async def test_google_drive_provider():
    provider = GoogleDriveProvider()
    result = await provider.execute()
    assert result["provider"] == "google_drive"
    assert result["data"]["status"] == "mock"

@pytest.mark.asyncio
async def test_google_gmail_provider():
    provider = GoogleGmailProvider()
    result = await provider.execute()
    assert result["provider"] == "google_gmail"
    assert result["data"]["status"] == "mock"

@pytest.mark.asyncio
async def test_google_calendar_provider():
    provider = GoogleCalendarProvider()
    result = await provider.execute()
    assert result["provider"] == "google_calendar"
    assert result["data"]["status"] == "mock"

@pytest.mark.asyncio
async def test_google_docs_provider():
    provider = GoogleDocsProvider()
    result = await provider.execute()
    assert result["provider"] == "google_docs"
    assert result["data"]["status"] == "mock"

@pytest.mark.asyncio
async def test_evidence_store():
    store = EvidenceStore("runtime/evidence/test_evidence.db")
    await store.init()
    await store.store("test query", "test_provider", "fast", {"result": "test"}, task_id="test_123")
    results = await store.get_by_task("test_123")
    assert len(results) == 1
    assert results[0]["query"] == "test query"
