"""
Schémas de données et modèles Pydantic v2 pour E-ZzIO
"""

import operator
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    query: str
    messages: Annotated[list[dict[str, Any]], operator.add]
    route: Literal["rag", "direct", "self_repair", "agent"]
    answer: str
    sources: list[dict[str, Any]]
    model_used: str
    action_result: dict[str, Any]
    thread_id: str
    error: str | None


class ChatRequest(BaseModel):
    query: str = Field(description="Question ou instruction pour E-ZzIO")
    thread_id: str = Field(default="default_thread", description="Identifiant unique de la session / conversation")
    stream: bool = Field(default=False, description="Activer le streaming SSE")


class ChatResponse(BaseModel):
    query: str
    thread_id: str
    route: str
    model_used: str
    answer: str
    sources: list[dict[str, Any]] = Field(default_factory=list)


class RAGResult(BaseModel):
    query: str
    answer: str
    source_documents: list[dict[str, Any]] = Field(default_factory=list)
    chunks_retrieved: int = 0
    model_used: str = "ez-rag-expert"


class FilePatchRequest(BaseModel):
    file_path: str = Field(description="Chemin relatif ou absolu du fichier à modifier")
    target_content: str = Field(description="Contenu exact à remplacer")
    replacement_content: str = Field(description="Nouveau contenu")
    reason: str = Field(default="", description="Raison de la modification")


class FilePatchResult(BaseModel):
    file_path: str
    success: bool
    message: str
    ast_valid: bool = True
    diff: str = ""


class HealthStatus(BaseModel):
    ollama_ok: bool
    models_available: list[str]
    vectorstore_ok: bool
    total_indexed_documents: int
    error: str | None = None
