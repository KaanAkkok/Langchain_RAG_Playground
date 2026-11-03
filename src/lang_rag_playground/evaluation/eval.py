from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from langgraph.graph.state import CompiledStateGraph

from lang_rag_playground.core.logger import get_logger
from lang_rag_playground.core.settings import settings
from lang_rag_playground.evaluation.generation_evaluation_service import GenerationEvaluator
from lang_rag_playground.evaluation.retrieval_evaluation_service import RetrievalEvaluator
from lang_rag_playground.guardrails.guardrails import Guardrails
from lang_rag_playground.retrieval.reranking import build_reranker_chain
from lang_rag_playground.retrieval.retrieval_service import RetrievalService
from lang_rag_playground.retrieval.vectordb_service import AsyncQdrantVectorDBService

logger = get_logger(__name__)

GraphBuilder = Callable[..., CompiledStateGraph[Any, Any, Any, Any]]


async def init_evaluation_snapshot(
    vector_store: AsyncQdrantVectorDBService,
    collection_name: str = settings.VECTORDB_EVALUATION_COLLECTION_NAME,
    snapshot_location: Path | str = settings.EVAL_SNAPSHOT_PATH,
) -> None:
    if await vector_store.is_collection_exists(collection_name):
        await vector_store.delete_collection(collection_name)
    restored = await vector_store.restore_snapshot(collection_name, snapshot_location)
    if not restored:
        raise RuntimeError(
            f"Failed to restore snapshot for collection '{collection_name}' from '{snapshot_location}'"
        )


async def run_eval(
    vector_store: AsyncQdrantVectorDBService,
    graph_builder: GraphBuilder,
    guardrails_service: Guardrails,
    evaluation_type: Literal["retrieval", "generation", "all"] = "all",
    collection_name: str = settings.VECTORDB_EVALUATION_COLLECTION_NAME,
    snapshot_location: str | Path = settings.EVAL_SNAPSHOT_PATH,
    retrieval_top_k: int = settings.RERANK_CANDIDATES,
    evaluation_top_k: int = settings.TOP_K_CANDIDATES,
) -> dict[str, dict[str, dict[str, float]]]:
    await init_evaluation_snapshot(
        vector_store=vector_store,
        collection_name=collection_name,
        snapshot_location=snapshot_location,
    )
    retriever = RetrievalService(vector_store=vector_store, collection_name=collection_name)
    results = {}

    if evaluation_type in ["retrieval", "all"]:
        logger.info("Running retrieval evaluation...")
        retrieval_evaluator = RetrievalEvaluator(
            retriever=retriever,
            reranker_chain=build_reranker_chain(),
            collection_name=collection_name,
        )
        results["retrieval"] = await retrieval_evaluator.evaluate(
            retrieval_top_k=retrieval_top_k,
            evaluation_top_k=evaluation_top_k,
        )

    if evaluation_type in ["generation", "all"]:
        logger.info(f"Running generation evaluation on {graph_builder.__name__}...")
        # store and checkpointer are None: eval runs must not persist memories or threads
        graph = graph_builder(
            retrieval_service=retriever,
            guardrails_service=guardrails_service,
            store=None,
            checkpointer=None,
        )
        generation_evaluator = GenerationEvaluator(graph=graph)
        results["generation"] = await generation_evaluator.evaluate()

    return results


if __name__ == "__main__":
    import asyncio

    from lang_rag_playground.graphs.graph import agentic_graph
    from lang_rag_playground.services.llm import build_embedding_model

    results = asyncio.run(
        run_eval(
            vector_store=AsyncQdrantVectorDBService(embedding=build_embedding_model()),
            graph_builder=agentic_graph,
            guardrails_service=Guardrails(),
            evaluation_type="retrieval",
        )
    )
    print("Evaluation Results:", results)
