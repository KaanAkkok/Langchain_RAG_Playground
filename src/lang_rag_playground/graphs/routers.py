from typing import Literal

from lang_rag_playground.core.settings import settings
from lang_rag_playground.models.agent_state_model import AgentState


def route_after_input_guardrails(state: AgentState) -> Literal["blocked", "intent"]:
    if not state.get("is_input_safe"):
        return "blocked"
    return "intent"


# Workflow graph only: the agentic graph lets the assistant decide whether to search.
def route_after_memory_recall(state: AgentState) -> Literal["retrieval", "assistant"]:
    if state.get("intent") == "knowledge_question":
        return "retrieval"
    return "assistant"


def route_after_judge(
    state: AgentState,
    max_retries: int = settings.JUDGE_MAX_RETRIES,
) -> Literal["blocked", "output_guardrails", "assistant"]:
    if state.get("judge_blocked"):
        return "blocked"
    if state.get("judge_passed"):
        return "output_guardrails"
    if state.get("retry_count", 0) >= max_retries:
        return "output_guardrails"
    return "assistant"


def route_after_output_guardrails(state: AgentState, batch_size: int = settings.LONG_TERM_MEMORY_BATCH_SIZE) -> Literal["memory_extract", "__end__"]:
    if len(state["messages"]) % batch_size == 0:
        return "memory_extract"
    return "__end__"