from uuid import uuid4

from langgraph.runtime import Runtime
from langchain_core.runnables import Runnable
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from lang_rag_playground.models.agent_state_model import AgentState
from lang_rag_playground.models.context_model import Context
from lang_rag_playground.core.settings import settings
from lang_rag_playground.nodes.utils import trim_history
from lang_rag_playground.prompts.prompts import MEMORY_PROMPT
from lang_rag_playground.services.llm import build_chat_model
from lang_rag_playground.schemas.memory_schema import MemoryExtraction

from lang_rag_playground.core.logger import get_logger

logger = get_logger(__name__)


MEMORY_TEMPLATE = ChatPromptTemplate.from_messages(
    [
        ("system", MEMORY_PROMPT),
        MessagesPlaceholder("history"),
    ]
)


def build_memory_extract_chain(
    model_name: str = settings.GEMINI_MEMORY_MODEL,
    temperature: float = settings.MEMORY_TEMPERATURE,
) -> Runnable:
    llm = build_chat_model(model_name, temperature)
    return MEMORY_TEMPLATE | llm.with_structured_output(MemoryExtraction)


def make_memory_recall_node(
    limit: int = settings.LONG_TERM_MEMORY_SEARCH_LIMIT,
    min_score: float = settings.LONG_TERM_MEMORY_MIN_SCORE,
):
    async def memory_recall_node(state: AgentState, runtime: Runtime[Context]) -> dict:
        memory_store = runtime.store
        if memory_store is None:
            return {"memories": []}
        # Memory is optional: if the search fails, answer without it.
        try:
            items = await memory_store.asearch(
                (runtime.context.user_id, "memories"),
                query=state["resolved_query"],
                limit=limit,
            )
        except Exception as e:
            logger.warning(f"Failed to search memories: {e}")
            return {"memories": []}
        if not items:
            return {"memories": []}
        memories = []
        for item in items:
            if item.score is not None and item.score >= min_score:
                memories.append(item.value["content"])
        return {"memories": memories}
    return memory_recall_node


def make_memory_extract_node(
    chain: Runnable,
    threshold: float = settings.LONG_TERM_MEMORY_CONFIDENCE_THRESHOLD,
    max_history_tokens: int = settings.MAX_HISTORY_TOKENS,
):
    async def memory_extract_node(state: AgentState, runtime: Runtime[Context]) -> dict:
        memory_store = runtime.store
        if memory_store is None:
            return {}
        history = trim_history(state, max_tokens=max_history_tokens)
        # The answer is already produced; a memory failure must not fail the turn.
        try:
            response = await chain.ainvoke({"history": history})
        except Exception as e:
            logger.warning(f"Failed to invoke memory extraction chain: {e}")
            return {}
        if not isinstance(response, MemoryExtraction):
            logger.warning("The response is not of type MemoryExtraction class.")
            return {}
        for memory in response.memories:
            if memory.confidence < threshold:
                continue
            try:
                await memory_store.aput(
                    (runtime.context.user_id, "memories"),
                    key=str(uuid4()),
                    value=memory.model_dump(),
                )
            except Exception as e:
                logger.warning(f"Failed to store memory: {e}")
        return {}
    return memory_extract_node
        
