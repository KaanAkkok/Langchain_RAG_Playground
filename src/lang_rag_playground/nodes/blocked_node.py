from langchain_core.messages import AIMessage

from lang_rag_playground.core.logger import get_logger
from lang_rag_playground.models.agent_state_model import AgentState

logger = get_logger(__name__)

BLOCKED_RESPONSE = "Girilen mesaj güvenlik kontrollerini geçemedi ve işlenemedi. Lütfen başka bir mesaj gönderin."


async def blocked_response_node(state: AgentState) -> dict:
    reason = "judge" if state.get("judge_blocked") else "input guardrails"
    logger.warning(f"Turn blocked by {reason}; sending refusal message.")
    message = state.get("security_message") or BLOCKED_RESPONSE
    logger.info(f"Sending blocked response: {message}")
    return {"messages": [AIMessage(content=message)]}
