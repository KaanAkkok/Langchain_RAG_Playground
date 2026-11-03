from collections.abc import Sequence
from typing import Any, cast

from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware, ToolRetryMiddleware
from langchain.agents.structured_output import ToolStrategy
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable
from langgraph.errors import GraphRecursionError

from lang_rag_playground.core.logger import get_logger
from lang_rag_playground.core.settings import settings
from lang_rag_playground.models.agent_context_model import AgentContext
from lang_rag_playground.models.agent_state_model import AgentState
from lang_rag_playground.nodes.utils import (
    format_feedback,
    format_sources,
    get_user_last_message,
    trim_history,
)
from lang_rag_playground.prompts.prompts import TOOL_PROMPT, ASSISTANT_PROMPT
from lang_rag_playground.retrieval.retrieval_service import RetrievalService
from lang_rag_playground.schemas.assistant_schema import AssistantResponse
from lang_rag_playground.services.llm import build_chat_model
from lang_rag_playground.tools.retrieve_tool import make_search_documents_tool

logger = get_logger(__name__)


_CONTEXT_SECTIONS = (
    "\n\n## Kullanıcı hakkında bilinenler\n{memories}\n\n## Görev\n{intent}"
)
WORKFLOW_ASSISTANT_TEMPLATE = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            ASSISTANT_PROMPT
            + _CONTEXT_SECTIONS
            + "\n\n## Kaynaklar\n{sources}\n\n{feedback}",
        ),
        MessagesPlaceholder("history"),
    ]
)
AGENT_ASSISTANT_TEMPLATE = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            ASSISTANT_PROMPT
            + "\n\n"
            + TOOL_PROMPT
            + _CONTEXT_SECTIONS
            + "\n\n## Önerilen arama sorgusu\n{resolved_query}\n\n{feedback}",
        ),
        MessagesPlaceholder("history"),
    ]
)
NOT_FOUND_ANSWER = "Bu bilgiyi yüklenen dokümanlarda bulamadım."


def _format_memories(state: AgentState) -> str:
    return "\n".join(f"- {m}" for m in state.get("memories") or []) or "(yok)"


def _assistant_update(response: AssistantResponse, sources: list[Document]) -> dict:
    cited_numbers = sorted(
        {n for n in response.cited_sources if 1 <= n <= len(sources)}
    )
    invalid_numbers = sorted(set(response.cited_sources) - set(cited_numbers))
    if invalid_numbers:
        logger.warning(
            f"Assistant cited non-existent sources {invalid_numbers} (available: 1-{len(sources)}); dropped."
        )
    logger.info(
        f"Answer generated ({len(response.answer)} chars), "
        f"sources: {len(sources)}, cited: {cited_numbers}"
    )
    logger.debug(f"Answer: {response.answer}")
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
        if state.get("feedback"):
            logger.info(
                f"Rewriting answer with judge feedback (attempt {state.get('retry_count', 0) + 1})."
            )
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
            ToolCallLimitMiddleware(
                tool_name="search_documents", run_limit=settings.MAX_TOOL_CALLS
            ),
            ToolRetryMiddleware(
                max_retries=settings.TOOL_MAX_RETRIES,
                on_failure=_tool_failure_message,
            ),
        ],
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
        if state.get("feedback"):
            logger.info(
                f"Rerunning agent with judge feedback (attempt {state.get('retry_count', 0) + 1})."
            )
        agent_context = AgentContext()
        try:
            result = await agent.ainvoke(
                {"messages": messages},
                context=agent_context,
            )
        except GraphRecursionError:
            logger.warning(
                "Agent hit the recursion limit; returning the not-found answer."
            )
            return _assistant_update(
                AssistantResponse(answer=NOT_FOUND_ANSWER), agent_context.sources
            )
        search_queries = [
            call["args"].get("query")
            for message in result["messages"]
            for call in getattr(message, "tool_calls", None) or []
            if call["name"] == "search_documents"
        ]
        logger.info(
            f"Agent made {len(search_queries)} search call(s): {search_queries}"
        )
        response = result.get("structured_response")
        if not isinstance(response, AssistantResponse):
            last_text = result["messages"][-1].text if result.get("messages") else ""
            if last_text.strip():
                logger.warning(
                    "Agent answered in plain text without AssistantResponse; using it without citations."
                )
                response = AssistantResponse(answer=last_text, cited_sources=[])
            else:
                logger.warning(
                    "Agent returned no answer; returning the not-found answer."
                )
                response = AssistantResponse(answer=NOT_FOUND_ANSWER, cited_sources=[])
        return _assistant_update(response, agent_context.sources)

    return assistant_node
