from typing import Any, Sequence, cast

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.agents.middleware import ToolCallLimitMiddleware, ToolRetryMiddleware

from lang_rag_playground.core.settings import settings
from lang_rag_playground.models.agent_state_model import AgentState
from lang_rag_playground.nodes.utils import (
    format_feedback,
    format_sources,
    get_user_last_message,
    trim_history,
)
from lang_rag_playground.prompts.prompts import ASSISTANT_AGENT_PROMPT, ASSISTANT_PROMPT
from lang_rag_playground.schemas.assistant_schema import AssistantResponse
from lang_rag_playground.services.llm import build_chat_model
from lang_rag_playground.retrieval.retrieval_service import RetrievalService
from lang_rag_playground.tools.search_tools import make_search_documents_tool
from lang_rag_playground.models.agent_context_model import AgentContext
from lang_rag_playground.core.logger import get_logger

logger = get_logger(__name__)


_CONTEXT_SECTIONS = "\n\n## Kullanıcı hakkında bilinenler\n{memories}\n\n## Görev\n{intent}"
WORKFLOW_ASSISTANT_TEMPLATE = ChatPromptTemplate.from_messages(
    [
        ("system", ASSISTANT_PROMPT + _CONTEXT_SECTIONS + "\n\n## Kaynaklar\n{sources}\n\n{feedback}"),
        MessagesPlaceholder("history"),
    ]
)
AGENT_ASSISTANT_TEMPLATE = ChatPromptTemplate.from_messages(
    [
        ("system", ASSISTANT_PROMPT + "\n\n" + ASSISTANT_AGENT_PROMPT + _CONTEXT_SECTIONS + "\n\n## Önerilen arama sorgusu\n{resolved_query}\n\n{feedback}"),
        MessagesPlaceholder("history"),
    ]
)


def _format_memories(state: AgentState) -> str:
    return "\n".join(f"- {m}" for m in state.get("memories") or []) or "(yok)"


def _assistant_update(response: AssistantResponse, sources: list[Document]) -> dict:
    cited_numbers = sorted(
        {n for n in response.cited_sources if 1 <= n <= len(sources)}
    )
    return {
        "generation": response.answer,
        "reranked_documents": sources,
        "cited_documents": [sources[n - 1] for n in cited_numbers],
    }


def build_assistant_chain(
    model_name: str = settings.GEMINI_ASSISTANT_MODEL,
    temperature: float = settings.ASSISTANT_TEMPERATURE,
) -> Runnable:
    llm = build_chat_model(model_name, temperature=temperature)
    return WORKFLOW_ASSISTANT_TEMPLATE | llm.with_structured_output(AssistantResponse)


def make_workflow_assistant_node(
    chain: Runnable,
    max_history_tokens: int = settings.MAX_HISTORY_TOKENS,
):
    async def assistant_node(state: AgentState) -> dict:
        last_user_msg = get_user_last_message(state)
        history = trim_history(state, max_history_tokens) or [last_user_msg]
        sources = state.get("reranked_documents") or []
        response = await chain.ainvoke(
            {
                "memories": _format_memories(state),
                "intent": state["intent"],
                "sources": format_sources(sources),
                "feedback": format_feedback(state.get("feedback")),
                "history": history,
            }
        )
        if not isinstance(response, AssistantResponse):
            raise TypeError("The response is not of type AssistantResponse class.")
        return _assistant_update(response, sources)

    return assistant_node


def _tool_failure_message(error: Exception) -> str:
    logger.error(f"Tool call failed after retries: {error}")
    return "Arama şu an yapılamıyor. Kullanıcıya dokümanlara şu an erişilemediğini söyle; bilgi uydurma."


def build_assistant_agent(
    retrieval_service: RetrievalService,
    reranker_chain: Runnable,
    model_name: str = settings.GEMINI_ASSISTANT_MODEL,
    temperature: float = settings.ASSISTANT_TEMPERATURE,
) -> Runnable:
    llm = build_chat_model(model_name, temperature=temperature)
    middleware_list = cast(
        Sequence[Any],
        [
            ToolCallLimitMiddleware(run_limit=settings.MAX_TOOL_CALLS),
            ToolRetryMiddleware(
                max_retries=settings.TOOL_MAX_RETRIES,
                on_failure=_tool_failure_message,
            ),
        ]
    )
    return create_agent(
        model=llm,
        tools=[make_search_documents_tool(retrieval_service, reranker_chain)],
        response_format=ToolStrategy(AssistantResponse),
        context_schema=AgentContext,
        middleware=middleware_list,
    )


def make_agent_assistant_node(
    agent: Runnable,
    max_history_tokens: int = settings.MAX_HISTORY_TOKENS,
):
    async def assistant_node(state: AgentState) -> dict:
        last_user_msg = get_user_last_message(state)
        history = trim_history(state, max_history_tokens) or [last_user_msg]
        messages = AGENT_ASSISTANT_TEMPLATE.format_messages(
            memories=_format_memories(state),
            intent=state["intent"],
            resolved_query=state.get("resolved_query") or last_user_msg.text,
            feedback=format_feedback(state.get("feedback")),
            history=history,
        )
        agent_context = AgentContext()
        result = await agent.ainvoke({"messages": messages}, context=agent_context)
        return _assistant_update(result["structured_response"], agent_context.sources)

    return assistant_node
