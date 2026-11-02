# NOTE: Used only by the workflow graph (`graphs/graph.py::workflow_graph`).
# The agentic graph reranks inside the `search_documents` tool instead.
# Both share the same logic in `retrieval/reranking.py`.
from langchain_core.runnables import Runnable

from lang_rag_playground.core.settings import settings
from lang_rag_playground.models.agent_state_model import AgentState
from lang_rag_playground.retrieval.reranking import rerank_documents


def make_reranker_node(
    chain: Runnable,
    top_k: int = settings.TOP_K_CANDIDATES,
    min_score: float = settings.MIN_RERANK_SCORE,
):
    async def reranker_node(state: AgentState) -> dict:
        candidates = state.get("raw_documents") or []
        if not candidates:
            return {"reranked_documents": []}
        reranked_documents = await rerank_documents(
            chain=chain,
            query=state["resolved_query"],
            candidates=candidates,
            top_k=top_k,
            min_score=min_score,
        )
        return {"reranked_documents": reranked_documents}

    return reranker_node
