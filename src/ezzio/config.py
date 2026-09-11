"""
Configuration centralisée pour E-ZzIO.
Alignée sur la stack Google Gemini :
- router_node -> gemini-3.5-flash-lite
- direct_node & rag_node -> gemini-3.7-flash
- self_repair_node -> gemini-3.1-pro
"""

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


class EzzioSettings(BaseSettings):
    # Inférence Cloud (Google Gemini Frontier Stack)
    use_gemini_primary: bool = Field(default=True, description="Utiliser Gemini en priorité pour des réponses instantanées")
    cloud_model_primary: str = Field(default="gemini-3.7-flash", description="Moteur principal pour orchestration et streaming SSE")
    cloud_model_lite: str = Field(default="gemini-3.5-flash-lite", description="Classifications d'intention ultra-rapides du routeur")
    cloud_model_pro: str = Field(default="gemini-3.1-pro", description="Tâches d'analyse complexe, AST lourd et auto-guérison")
    gemini_api_key: str | None = Field(default=None, description="Clé API Google Gemini")
    
    # Aliases de compatibilité
    @property
    def gemini_model(self) -> str:
        return self.cloud_model_primary

    @property
    def gemini_pro_model(self) -> str:
        return self.cloud_model_pro
    
    # Repli Souverain Local (Circuit Breaker Ollama)
    local_router_model: str = Field(default="ez-router", description="Modèle local pour la classification")
    local_core_model: str = Field(default="ez-core-safe", description="Modèle local pour les réponses logiques directes")
    local_rag_model: str = Field(default="ez-rag-expert", description="Modèle local pour la synthèse documentaire RAG")
    agent_model: str = Field(default="ez-agent-hermes", description="Modèle local agent pour les tâches autonomes")
    free_model: str = Field(default="ez-core-free", description="Modèle local non censuré")
    embedding_model: str = Field(default="bge-m3:latest", description="Modèle d'embedding vectoriel")
    
    # Aliases de compatibilité pour le code existant
    @property
    def router_model(self) -> str:
        return self.local_router_model

    @property
    def core_safe_model(self) -> str:
        return self.local_core_model

    @property
    def rag_expert_model(self) -> str:
        return self.local_rag_model

    # Réseau & Ollama
    ollama_url: str = Field(default="http://127.0.0.1:11434", description="URL IPv4 directe vers Ollama")
    
    # Chemins
    root_dir: Path = Field(default=Path("G:/AI/E-zzio").resolve())
    data_dir: Path = Field(default=Path("G:/AI/E-zzio/data").resolve())
    chroma_db_dir: Path = Field(default=Path("G:/AI/E-zzio/data/chroma_db").resolve())
    state_db_path: Path = Field(default=Path("G:/AI/E-zzio/data/ezzio_state.db").resolve())
    
    # API & Serveur
    api_host: str = Field(default="127.0.0.1")
    api_port: int = Field(default=8000)
    
    # Paramètres RAG
    chunk_size: int = 800
    chunk_overlap: int = 120
    top_k_retrieval: int = 3

    class Config:
        env_prefix = "EZZIO_"
        arbitrary_types_allowed = True


def _load_gemini_key() -> str | None:
    import os
    env_paths = [
        Path("G:/AI/E-zzio/secrets/.env"),
        Path("secrets/.env"),
        Path(__file__).resolve().parent.parent.parent / "secrets" / ".env"
    ]
    for p in env_paths:
        if p.exists():
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "GEMINI_API_KEY=" in line:
                        return line.split("=", 1)[1].strip().strip("\"'")
            except Exception:
                pass
    return os.environ.get("GEMINI_API_KEY")


# Instance globale partagée
settings = EzzioSettings()
if not settings.gemini_api_key:
    settings.gemini_api_key = _load_gemini_key()
