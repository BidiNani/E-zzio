"""
Outils de diagnostic système et d'exécution de tests pour E-ZzIO.
"""

import asyncio
import logging
from typing import Any
import httpx

from ezzio.config import settings
from ezzio.schemas import HealthStatus

logger = logging.getLogger("EzzioSystemTools")


async def check_ollama_health() -> HealthStatus:
    """Vérifie la connectivité Ollama et la liste des modèles disponibles."""
    url = f"{settings.ollama_url}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name") for m in data.get("models", [])]
                return HealthStatus(
                    ollama_ok=True,
                    models_available=models,
                    vectorstore_ok=settings.chroma_db_dir.exists(),
                    total_indexed_documents=0,
                )
            else:
                return HealthStatus(
                    ollama_ok=False,
                    models_available=[],
                    vectorstore_ok=settings.chroma_db_dir.exists(),
                    total_indexed_documents=0,
                    error=f"HTTP {resp.status_code}"
                )
    except Exception as exc:
        return HealthStatus(
            ollama_ok=False,
            models_available=[],
            vectorstore_ok=settings.chroma_db_dir.exists(),
            total_indexed_documents=0,
            error=str(exc)
        )


async def run_local_tests() -> dict[str, Any]:
    """Exécute la suite de tests pytest de manière asynchrone."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "pytest", "-v", "--tb=short",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(settings.root_dir)
        )
        stdout, stderr = await proc.communicate()
        return {
            "exit_code": proc.returncode,
            "success": proc.returncode == 0,
            "stdout": stdout.decode("utf-8", errors="ignore"),
            "stderr": stderr.decode("utf-8", errors="ignore"),
        }
    except Exception as exc:
        return {
            "exit_code": -1,
            "success": False,
            "stdout": "",
            "stderr": str(exc),
        }
