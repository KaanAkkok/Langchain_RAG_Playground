from langchain_core.messages import AIMessage

from lang_rag_playground.models.agent_state_model import AgentState

BLOCKED_RESPONSE = "Girilen mesaj güvenlik kontrollerini geçemedi ve işlenemedi. Lütfen başka bir mesaj gönderin."


async def blocked_response_node(state: AgentState) -> dict:
    message = state.get("security_message") or BLOCKED_RESPONSE
    return {"messages": [AIMessage(content=message)]}
