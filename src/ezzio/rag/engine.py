"""
Moteur RAG Asynchrone Haute Performance pour E-ZzIO.
Embeddings : bge-m3:latest (ou ChromaDB)
Synthèse : Gemini 3.7 Flash (Cloud Flash ultra-rapide) avec repli sur ez-rag-expert local.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

from ezzio.config import settings
from ezzio.llm.client import get_llm_client
from ezzio.rag.loader import CodebaseLoader
from ezzio.schemas import RAGResult

logger = logging.getLogger("EzzioRAG")

_GLOBAL_RAG_ENGINE: "LocalRAGEngine | None" = None


class LocalRAGEngine:
    def __init__(
        self,
        persist_directory: Path | str = settings.chroma_db_dir,
        embedding_model: str = settings.embedding_model,
        llm_model: str = settings.rag_expert_model,
        ollama_url: str = settings.ollama_url,
    ) -> None:
        self.persist_dir = Path(persist_directory)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.ollama_url = ollama_url
        self.llm_model_name = llm_model

        self._embeddings = None
        self._vector_store = None
        self.loader = CodebaseLoader()

    @property
    def embeddings(self):
        if self._embeddings is None:
            self._embeddings = OllamaEmbeddings(
                model=self.embedding_model_name if hasattr(self, 'embedding_model_name') else settings.embedding_model,
                base_url=self.ollama_url
            )
        return self._embeddings

    @property
    def vector_store(self):
        if self._vector_store is None:
            self._vector_store = Chroma(
                collection_name="ezzio_knowledge",
                embedding_function=self.embeddings,
                persist_directory=str(self.persist_dir)
            )
        return self._vector_store

    @staticmethod
    def _format_docs(docs: list[Any]) -> str:
        formatted_chunks = []
        for i, doc in enumerate(docs, start=1):
            source = doc.metadata.get("source", "inconnu")
            path = doc.metadata.get("path", source)
            formatted_chunks.append(f"[Extrait {i} | Fichier: {path}]\n{doc.page_content}")
        return "\n\n".join(formatted_chunks)

    async def aquery(self, question: str, top_k: int = settings.top_k_retrieval) -> RAGResult:
        try:
            docs = []
            try:
                retriever = self.vector_store.as_retriever(search_kwargs={"k": top_k})
                docs = await asyncio.to_thread(retriever.invoke, question)
            except Exception as embed_exc:
                logger.warning("Goulet ou indisponibilité bge-m3 (%s) -> Repli instantané sur recherche textuelle.", embed_exc)
                all_docs = self.loader.load_directory(settings.root_dir)
                keywords = [w.lower() for w in question.split() if len(w) > 3]
                scored = []
                for d in all_docs:
                    score = sum(1 for kw in keywords if kw in d.page_content.lower())
                    if score > 0:
                        scored.append((score, d))
                scored.sort(key=lambda x: x[0], reverse=True)
                docs = [d for _, d in scored[:top_k]]

            if not docs:
                return RAGResult(
                    query=question,
                    answer="Information non présente dans les documents.",
                    source_documents=[],
                    chunks_retrieved=0,
                    model_used=settings.gemini_model
                )

            context_str = self._format_docs(docs)
            system_prompt = (
                "Tu es le spécialiste documentaire et architectural d'E-ZzIO.\n"
                "Réponds à la question avec précision en utilisant les extraits documentaires fournis ci-dessous.\n"
                "Si la réponse ne figure pas dans le contexte, dis clairement : 'Information non présente dans les documents.'\n"
                "Sois clair, concis et rigoureux."
            )
            full_prompt = f"Extraits documentaires :\n{context_str}\n\nQuestion de l'utilisateur : {question}"

            llm = get_llm_client()
            answer, model_used = await llm.ainvoke(
                prompt=full_prompt,
                system_prompt=system_prompt,
                temperature=0.0,
                model=settings.cloud_model_primary
            )

            sources = [
                {"content": d.page_content, "metadata": d.metadata}
                for d in docs
            ]

            return RAGResult(
                query=question,
                answer=answer.strip(),
                source_documents=sources,
                chunks_retrieved=len(docs),
                model_used=model_used
            )

        except Exception as exc:
            logger.error("Erreur lors de la requête RAG : %s", exc, exc_info=True)
            return RAGResult(
                query=question,
                answer=f"Erreur d'exécution RAG : {str(exc)}",
                source_documents=[],
                chunks_retrieved=0,
                model_used="error"
            )

    def query(self, question: str, top_k: int = settings.top_k_retrieval) -> RAGResult:
        return asyncio.run(self.aquery(question, top_k=top_k))

    def ingest_codebase(self) -> int:
        documents = self.loader.load_and_split()
        if not documents:
            logger.warning("Aucun document trouvé pour l'ingestion.")
            return 0

        self.vector_store.add_documents(documents)
        logger.info("Ingestion terminée : %d segments vectorisés.", len(documents))
        return len(documents)


def get_rag_engine() -> LocalRAGEngine:
    global _GLOBAL_RAG_ENGINE
    if _GLOBAL_RAG_ENGINE is None:
        _GLOBAL_RAG_ENGINE = LocalRAGEngine()
    return _GLOBAL_RAG_ENGINE
