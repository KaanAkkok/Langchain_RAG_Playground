# NOTE: Used only by the workflow graph (`graphs/graph.py::workflow_graph`).
# The agentic graph searches inside the `search_documents` tool (`tools/search_tools.py`),
# where the agent picks the query itself.
from lang_rag_playground.core.settings import settings
from lang_rag_playground.models.agent_state_model import AgentState
from lang_rag_playground.retrieval.retrieval_service import RetrievalService


def make_retrieval_node(
    retrieval_service: RetrievalService, top_k: int = settings.RERANK_CANDIDATES
):
    async def retrieval_node(state: AgentState) -> dict:
        documents = await retrieval_service.search(query=state["resolved_query"], top_k=top_k)
        return {"raw_documents": documents}

    return retrieval_node
