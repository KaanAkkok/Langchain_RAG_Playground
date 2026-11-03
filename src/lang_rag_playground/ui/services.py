from dataclasses import dataclass
from typing import Any, Literal

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph

from lang_rag_playground.core.settings import settings
from lang_rag_playground.evaluation.eval import GraphBuilder
from lang_rag_playground.graphs.graph import agentic_graph, workflow_graph
from lang_rag_playground.guardrails.guardrails import Guardrails
from lang_rag_playground.ingestion.document_chunker import DocumentChunker
from lang_rag_playground.ingestion.document_extractor import DocumentExtractor
from lang_rag_playground.memory.qdrant_store import QdrantMemoryStore
from lang_rag_playground.retrieval.retrieval_service import RetrievalService
from lang_rag_playground.retrieval.vectordb_service import AsyncQdrantVectorDBService
from lang_rag_playground.services.llm import build_embedding_model

_REQUIRED_MODEL_SETTINGS = (
    "GEMINI_EMBEDDING_MODEL",
    "GEMINI_INTENT_MODEL",
    "GEMINI_RERANKER_MODEL",
    "GEMINI_ASSISTANT_MODEL",
    "GEMINI_JUDGE_MODEL",
    "GEMINI_MEMORY_MODEL",
)


@dataclass
class AppServices:
    graph: CompiledStateGraph[Any, Any, Any, Any]
    graph_builder: GraphBuilder
    vectordb: AsyncQdrantVectorDBService
    checkpointer: InMemorySaver
    store: QdrantMemoryStore
    retrieval_service: RetrievalService
    guardrails: Guardrails
    extractor: DocumentExtractor
    chunker: DocumentChunker
    mermaid_diagram: str


def _validate_settings() -> None:
    missing: list[str] = []
    if not settings.GEMINI_API_KEY.get_secret_value().strip():
        missing.append("GEMINI_API_KEY")
    for attr in _REQUIRED_MODEL_SETTINGS:
        val = getattr(settings, attr, "")
        if not str(val).strip():
            missing.append(attr)
    if missing:
        raise RuntimeError(
            f"Eksik ortam değişkenleri (.env kontrol edin): {', '.join(missing)}"
        )


def build_app_services(graph_type: Literal["agentic", "workflow"]) -> AppServices:
    _validate_settings()

    embeddings = build_embedding_model()
    api_key = settings.QDRANT_API_KEY.get_secret_value().strip() or None
    vectordb = AsyncQdrantVectorDBService(
        embeddings,
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
        api_key=api_key,
    )

    try:
        vectordb.client.get_collections()
    except Exception as e:
        raise RuntimeError(
            f"Qdrant çalışmıyor (http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}). "
            "Başlatmak için: docker run -p 6333:6333 qdrant/qdrant"
        ) from e

    store = QdrantMemoryStore(vector_db=vectordb)
    store.ensure_collection()
    checkpointer = InMemorySaver()
    guardrails = Guardrails()
    retrieval_service = RetrievalService(
        vectordb, settings.VECTORDB_KNOWLEDGE_COLLECTION_NAME
    )
    extractor = DocumentExtractor()
    chunker = DocumentChunker(embedding_model=embeddings)

    if graph_type == "agentic":
        graph_builder = agentic_graph
    else:
        graph_builder = workflow_graph
    graph = graph_builder(retrieval_service, guardrails, store, checkpointer)
    mermaid_diagram = graph.get_graph().draw_mermaid()

    return AppServices(
        graph=graph,
        graph_builder=graph_builder,
        vectordb=vectordb,
        checkpointer=checkpointer,
        store=store,
        retrieval_service=retrieval_service,
        guardrails=guardrails,
        extractor=extractor,
        chunker=chunker,
        mermaid_diagram=mermaid_diagram,
    )
