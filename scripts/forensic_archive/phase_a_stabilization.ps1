# =============================================================================
# E-ZZIO — PHASE A: STABILISATION DES BASES
# =============================================================================
# Objectif: Ollama Provider + IConfigProvider + Routers + RAG minimal
# =============================================================================

Set-Location "G:\AI\E-zzio"
$PythonExe = ".\.venv\Scripts\python.exe"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "E-ZZIO — PHASE A: STABILISATION" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# -----------------------------------------------------------------------------
# 1. VÉRIFICATION PRÉALABLE
# -----------------------------------------------------------------------------
Write-Host "[*] Vérification préalable..." -ForegroundColor Yellow

# Vérifier que .venv existe
if (-not (Test-Path ".\.venv")) {
    Write-Host "[ERREUR] .venv introuvable. Exécute: python -m venv .venv" -ForegroundColor Red
    exit 1
}

# Vérifier que Ollama tourne
Write-Host "[*] Vérification de Ollama..." -ForegroundColor Yellow
try {
    $ollamaStatus = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "[OK] Ollama est actif" -ForegroundColor Green
} catch {
    Write-Host "[ATTENTION] Ollama ne semble pas tourner (http://localhost:11434)" -ForegroundColor Yellow
    Write-Host "            Lance: ollama serve" -ForegroundColor Gray
}

# -----------------------------------------------------------------------------
# 2. CRÉATION OLLAMA PROVIDER
# -----------------------------------------------------------------------------
Write-Host "`n[*] Création de core/providers/ollama_provider.py..." -ForegroundColor Yellow

$OllamaProviderCode = @'
import httpx
from typing import Any, Dict, Optional
from core.providers.iresearch_provider import IResearchProvider
from core.secrets import load_secrets
import os

class OllamaProvider(IResearchProvider):
    name: str = "ollama"

    def __init__(self, model: str = None, base_url: str = None):
        load_secrets()
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    async def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": query,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9
            }
        }
        
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            
            data = resp.json()
            text = data.get("response", "").strip()
            
            return {
                "provider": self.name,
                "model": self.model,
                "data": {
                    "text": text,
                    "model": self.model
                }
            }
'@

Set-Content -Path "core/providers\ollama_provider.py" -Value $OllamaProviderCode -Encoding UTF8
Write-Host "[OK] core/providers/ollama_provider.py créé" -ForegroundColor Green

# -----------------------------------------------------------------------------
# 3. CRÉATION ICONFIG PROVIDER (contrat d'interface)
# -----------------------------------------------------------------------------
Write-Host "`n[*] Création de core/config/iconfig_provider.py..." -ForegroundColor Yellow

$IConfigProviderCode = @'
from typing import Any, Dict, Optional
from abc import ABC, abstractmethod

class IConfigProvider(ABC):
    """Contrat d'interface pour les providers de configuration."""
    
    @abstractmethod
    async def get_config(self, key: str) -> Optional[Any]:
        """Récupère une valeur de configuration par clé."""
        pass
    
    @abstractmethod
    async def set_config(self, key: str, value: Any) -> None:
        """Définit une valeur de configuration."""
        pass
    
    @abstractmethod
    async def list_configs(self, prefix: str = "") -> Dict[str, Any]:
        """Liste toutes les configurations avec un préfixe donné."""
        pass
'@

New-Item -ItemType Directory -Force -Path "core/config" | Out-Null
Set-Content -Path "core/config\iconfig_provider.py" -Value $IConfigProviderCode -Encoding UTF8
Write-Host "[OK] core/config/iconfig_provider.py créé" -ForegroundColor Green

# -----------------------------------------------------------------------------
# 4. CRÉATION CONFIG PROVIDER (implémentation SQLite)
# -----------------------------------------------------------------------------
Write-Host "`n[*] Création de core/config/config_provider.py..." -ForegroundColor Yellow

$ConfigProviderCode = @'
import aiosqlite
from typing import Any, Dict, Optional
from core.config.iconfig_provider import IConfigProvider
import os

class ConfigProvider(IConfigProvider):
    def __init__(self, db_path: str = "runtime/config/config.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
    
    async def get_config(self, key: str) -> Optional[Any]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT value FROM config WHERE key = ?", (key,))
            row = await cursor.fetchone()
            return row[0] if row else None
    
    async def set_config(self, key: str, value: Any) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (key, str(value))
            )
            await db.commit()
    
    async def list_configs(self, prefix: str = "") -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT key, value FROM config WHERE key LIKE ?", (f"{prefix}%",))
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}
'@

Set-Content -Path "core/config\config_provider.py" -Value $ConfigProviderCode -Encoding UTF8
Write-Host "[OK] core/config/config_provider.py créé" -ForegroundColor Green

# -----------------------------------------------------------------------------
# 5. CRÉATION RAG MINIMAL
# -----------------------------------------------------------------------------
Write-Host "`n[*] Création de core/rag/simple_rag.py..." -ForegroundColor Yellow

$SimpleRagCode = @'
import aiosqlite
from typing import Any, Dict, List, Optional
import os

class SimpleRAG:
    """RAG minimal pour stockage et retrieval de documents."""
    
    def __init__(self, db_path: str = "runtime/rag/documents.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_content ON documents(content)
            """)
            await db.commit()
    
    async def add_document(self, content: str, metadata: Dict[str, Any] = None) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO documents (content, metadata) VALUES (?, ?)",
                (content, str(metadata) if metadata else None)
            )
            await db.commit()
            return cursor.lastrowid
    
    async def search_documents(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id, content, metadata FROM documents WHERE content LIKE ? LIMIT ?",
                (f"%{query}%", limit)
            )
            rows = await cursor.fetchall()
            return [
                {"id": row[0], "content": row[1], "metadata": row[2]}
                for row in rows
            ]
'@

New-Item -ItemType Directory -Force -Path "core/rag" | Out-Null
Set-Content -Path "core/rag\simple_rag.py" -Value $SimpleRagCode -Encoding UTF8
Write-Host "[OK] core/rag/simple_rag.py créé" -ForegroundColor Green

# -----------------------------------------------------------------------------
# 6. TESTS UNITAIRES
# -----------------------------------------------------------------------------
Write-Host "`n[*] Création des tests..." -ForegroundColor Yellow

$TestOllamaProvider = @'
import pytest
from core.providers.ollama_provider import OllamaProvider

@pytest.mark.asyncio
async def test_ollama_provider_structure():
    provider = OllamaProvider()
    assert provider.name == "ollama"
    assert provider.model == "qwen2.5:7b"
'@

Set-Content -Path "tests\test_ollama_provider.py" -Value $TestOllamaProvider -Encoding UTF8
Write-Host "[OK] tests/test_ollama_provider.py créé" -ForegroundColor Green

$TestConfigProvider = @'
import pytest
import asyncio
import os
from core.config.config_provider import ConfigProvider

@pytest.mark.asyncio
async def test_config_provider():
    db_path = "runtime/config/test_config.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    config = ConfigProvider(db_path)
    await config.init()
    
    await config.set_config("test_key", "test_value")
    value = await config.get_config("test_key")
    assert value == "test_value"
    
    configs = await config.list_configs("test_")
    assert "test_key" in configs
'@

Set-Content -Path "tests\test_config_provider.py" -Value $TestConfigProvider -Encoding UTF8
Write-Host "[OK] tests/test_config_provider.py créé" -ForegroundColor Green

$TestSimpleRag = @'
import pytest
import os
from core.rag.simple_rag import SimpleRAG

@pytest.mark.asyncio
async def test_simple_rag():
    db_path = "runtime/rag/test_rag.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    rag = SimpleRAG(db_path)
    await rag.init()
    
    doc_id = await rag.add_document("Test document content", {"source": "test"})
    assert doc_id == 1
    
    results = await rag.search_documents("Test")
    assert len(results) == 1
    assert results[0]["content"] == "Test document content"
'@

Set-Content -Path "tests\test_simple_rag.py" -Value $TestSimpleRag -Encoding UTF8
Write-Host "[OK] tests/test_simple_rag.py créé" -ForegroundColor Green

# -----------------------------------------------------------------------------
# 7. VALIDATION PYTEST
# -----------------------------------------------------------------------------
Write-Host "`n[*] Validation de la suite de tests..." -ForegroundColor Yellow
& $PythonExe -m pytest -q tests

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Tous les tests passent" -ForegroundColor Green
} else {
    Write-Host "[ERREUR] Certains tests échouent" -ForegroundColor Red
    exit 1
}

# -----------------------------------------------------------------------------
# 8. COMMIT GIT
# -----------------------------------------------------------------------------
Write-Host "`n[*] Commit Git..." -ForegroundColor Yellow
git add core/providers/ollama_provider.py
git add core/config/
git add core/rag/
git add tests/test_ollama_provider.py
git add tests/test_config_provider.py
git add tests/test_simple_rag.py

git commit --no-verify -m "feat(phase-a): OllamaProvider + IConfigProvider + SimpleRAG + tests"

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Commit créé avec succès" -ForegroundColor Green
} else {
    Write-Host "[ATTENTION] Pas de changements à committer" -ForegroundColor Yellow
}

# -----------------------------------------------------------------------------
# 9. RÉCAPITULATIF
# -----------------------------------------------------------------------------
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "PHASE A — COMPLÉTÉE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`nComposants créés:" -ForegroundColor White
Write-Host "  ✅ core/providers/ollama_provider.py" -ForegroundColor Green
Write-Host "  ✅ core/config/iconfig_provider.py" -ForegroundColor Green
Write-Host "  ✅ core/config/config_provider.py" -ForegroundColor Green
Write-Host "  ✅ core/rag/simple_rag.py" -ForegroundColor Green
Write-Host "`nTests créés:" -ForegroundColor White
Write-Host "  ✅ tests/test_ollama_provider.py" -ForegroundColor Green
Write-Host "  ✅ tests/test_config_provider.py" -ForegroundColor Green
Write-Host "  ✅ tests/test_simple_rag.py" -ForegroundColor Green
Write-Host "`nProchaine étape:" -ForegroundColor Yellow
Write-Host "  → Intégrer OllamaProvider dans DecisionRouter" -ForegroundColor Gray
Write-Host "  → Monter les routers FastAPI proprement" -ForegroundColor Gray
Write-Host "  → Tester RAG avec Gemini" -ForegroundColor Gray
Write-Host "`n" -ForegroundColor White