from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable

from lang_rag_playground.core.logger import get_logger
from lang_rag_playground.core.settings import settings
from lang_rag_playground.models.agent_state_model import AgentState
from lang_rag_playground.nodes.utils import (
    get_user_last_message,
    trim_history,
)
from lang_rag_playground.prompts.prompts import INTENT_PROMPT
from lang_rag_playground.schemas.intent_schema import Intent
from lang_rag_playground.services.llm import build_chat_model

logger = get_logger(__name__)

INTENT_TEMPLATE = ChatPromptTemplate.from_messages(
    [
        ("system", INTENT_PROMPT),
        MessagesPlaceholder("history"),
    ]
)


def build_intent_chain(
    model_name: str = settings.GEMINI_INTENT_MODEL,
    temperature: float = settings.INTENT_TEMPERATURE,
) -> Runnable:
    llm = build_chat_model(model_name, temperature=temperature)
    return INTENT_TEMPLATE | llm.with_structured_output(Intent)


def make_intent_node(
    chain: Runnable,
    max_history_tokens: int = settings.MAX_HISTORY_TOKENS,
    min_confidence: float = settings.INTENT_MIN_CONFIDENCE,
):
    async def intent_node(state: AgentState) -> dict:
        last_user_msg = get_user_last_message(state)
        history = trim_history(state, max_tokens=max_history_tokens)
        response = await chain.ainvoke(
            {"input_text": last_user_msg.text, "history": history}
        )
        if not isinstance(response, Intent):
            raise TypeError("The response is not of type Intent class.")
        intent = response.intent if response.confidence >= min_confidence else "needs_clarification"
        if intent != response.intent:
            logger.warning(
                f"Low intent confidence ({response.confidence:.2f} < {min_confidence}): "
                f"'{response.intent}' downgraded to 'needs_clarification'."
            )
        logger.info(
            f"Intent: {intent} (confidence {response.confidence:.2f}), "
            f"resolved query: '{response.resolved_query}'"
        )
        return {
            "intent": intent,
            "intent_confidence": response.confidence,
            "resolved_query": response.resolved_query,
        }

    return intent_node
