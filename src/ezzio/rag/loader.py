"""
Chargeur et découpeur documentaire pour le codebase et la documentation d'E-ZzIO
"""

import logging
from pathlib import Path
from typing import Any
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ezzio.config import settings

logger = logging.getLogger("EzzioLoader")

IGNORE_DIRS = {
    ".venv", "venv", "__pycache__", ".pytest_cache", ".git", ".github",
    ".vscode", ".trae", "legacy_archive", "_forensic", "node_modules",
    "artifacts", "backups", "snapshot", "test_tmp", "data", "runtime",
    "v17", "v18", "v19", "tests", "_quarantine_dead_imports", "ezzio-ui",
    "deploy_scripts", "docker", "forge", "ollama_local_archive", "recovery",
    "registry", "secrets", "templates", "core", "providers", "tools"
}

IGNORE_FILES = {
    "EZZIO_CONTEXT.md", "uv.lock", "package-lock.json", "memory.db"
}

MAX_FILE_SIZE_BYTES = 500 * 1024  # 500 KB max par fichier
SUPPORTED_EXTENSIONS = (".md", ".py", ".json", ".ps1", ".toml", ".yaml", ".yml", ".txt")



class CodebaseLoader:
    def __init__(
        self,
        chunk_size: int = settings.chunk_size,
        chunk_overlap: int = settings.chunk_overlap,
    ) -> None:
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "    ", " ", ""]
        )

    def load_file(self, file_path: Path) -> list[Document]:
        if not file_path.is_file() or file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return []
        
        if file_path.name in IGNORE_FILES:
            return []

        try:
            if file_path.stat().st_size > MAX_FILE_SIZE_BYTES:
                logger.info("Fichier ignoré car trop volumineux (> 500KB) : %s", file_path.name)
                return []
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            if not content.strip():
                return []
            
            relative_path = file_path.relative_to(settings.root_dir).as_posix() if file_path.is_relative_to(settings.root_dir) else file_path.name
            
            metadata = {
                "source": file_path.name,
                "path": relative_path,
                "extension": file_path.suffix.lower(),
                "file_type": "code" if file_path.suffix in (".py", ".ps1") else "doc",
            }
            
            raw_doc = Document(page_content=content, metadata=metadata)
            return self.text_splitter.split_documents([raw_doc])
        except Exception as exc:
            logger.warning("Erreur lors de la lecture de %s : %s", file_path, exc)
            return []

    def load_directory(
        self,
        directory_path: Path | str,
        recursive: bool = True,
    ) -> list[Document]:
        target_dir = Path(directory_path)
        if not target_dir.exists() or not target_dir.is_dir():
            return []

        all_docs: list[Document] = []
        
        for item in target_dir.iterdir():
            if item.name in IGNORE_DIRS or item.name.startswith("."):
                continue
                
            if item.is_dir() and recursive:
                all_docs.extend(self.load_directory(item, recursive=True))
            elif item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS:
                all_docs.extend(self.load_file(item))

        return all_docs
