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
    # TODO (Görev 5): Öğrenci Rehberi > Görev 5
    # Adım 1: build_chat_model(model_name, temperature=temperature) ile LLM oluştur
    # Adım 2: INTENT_TEMPLATE | llm.with_structured_output(Intent) zincirini döndür
    raise NotImplementedError("TODO (Görev 5): Öğrenci Rehberi > Görev 5")


def make_intent_node(
    chain: Runnable,
    max_history_tokens: int = settings.MAX_HISTORY_TOKENS,
    min_confidence: float = settings.INTENT_MIN_CONFIDENCE,
):
    async def intent_node(state: AgentState) -> dict:
        # TODO (Görev 5): Öğrenci Rehberi > Görev 5
        # Adım 3: son kullanıcı mesajını al, geçmişi trim_history ile kırp
        # Adım 4: chain.ainvoke({"input_text": ..., "history": ...}) çağır
        raise NotImplementedError("TODO (Görev 5): Öğrenci Rehberi > Görev 5")
        if not isinstance(response, Intent):
            raise TypeError("The response is not of type Intent class.")
        # TODO (Görev 5): Öğrenci Rehberi > Görev 5
        # Adım 5: confidence < min_confidence ise intent'i "needs_clarification" yap
        raise NotImplementedError("TODO (Görev 5): Öğrenci Rehberi > Görev 5")
        if intent != response.intent:
            logger.warning(
                f"Low intent confidence ({response.confidence:.2f} < {min_confidence}): "
                f"'{response.intent}' downgraded to 'needs_clarification'."
            )
        logger.info(
            f"Intent: {intent} (confidence {response.confidence:.2f}), "
            f"resolved query: '{response.resolved_query}'"
        )
        # TODO (Görev 5): Öğrenci Rehberi > Görev 5
        # Adım 6: intent, intent_confidence, resolved_query alanlarını döndür
        raise NotImplementedError("TODO (Görev 5): Öğrenci Rehberi > Görev 5")

    return intent_node
