from lang_rag_playground.core.logger import get_logger
from lang_rag_playground.core.settings import settings
from lang_rag_playground.models.agent_state_model import AgentState
from lang_rag_playground.retrieval.retrieval_service import RetrievalService

logger = get_logger(__name__)


def make_retrieval_node(
    retrieval_service: RetrievalService, top_k: int = settings.RERANK_CANDIDATES
):
    async def retrieval_node(state: AgentState) -> dict:
        query = state["resolved_query"]
        documents = await retrieval_service.search(query=query, top_k=top_k)
        if not documents:
            logger.warning(f"Retrieval returned no candidates for query '{query}'.")
        else:
            logger.info(f"Retrieved {len(documents)} candidates for query '{query}'.")
        return {"raw_documents": documents}

    return retrieval_node
