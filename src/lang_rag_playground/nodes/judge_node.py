from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from lang_rag_playground.core.logger import get_logger
from lang_rag_playground.core.settings import settings
from lang_rag_playground.models.agent_state_model import AgentState
from lang_rag_playground.nodes.utils import format_sources
from lang_rag_playground.prompts.prompts import JUDGE_PROMPT
from lang_rag_playground.schemas.judge_schema import JudgeSchema
from lang_rag_playground.services.llm import build_chat_model

logger = get_logger(__name__)

JUDGE_TEMPLATE = ChatPromptTemplate.from_messages(
    [
        ("system", JUDGE_PROMPT),
        (
            "human",
            "## Niyet\n{intent}\n\n## Soru\n{question}\n\n## Bağlam\n{context}\n\n## Yanıt\n{answer}",
        ),
    ]
)


def build_judge_chain(
    model_name: str = settings.GEMINI_JUDGE_MODEL,
    temperature: float = settings.JUDGE_TEMPERATURE,
) -> Runnable:
    llm = build_chat_model(model_name, temperature=temperature)
    return JUDGE_TEMPLATE | llm.with_structured_output(JudgeSchema)


def make_judge_node(
    chain: Runnable,
):
    async def judge_node(state: AgentState) -> dict:
        reranked_documents = state.get("reranked_documents") or []
        question = state["resolved_query"]
        answer = state["generation"]
        context = format_sources(reranked_documents)
        intent = state["intent"]
        payload = {
            "question": question,
            "answer": answer,
            "context": context,
            "intent": intent,
        }
        response = await chain.ainvoke(payload)
        if not isinstance(response, JudgeSchema):
            raise TypeError("The response is not of type JudgeSchema class.")
        if intent == "knowledge_question":
            passed = (
                response.faithfulness
                and response.relevancy
                and not response.hallucination
            )
        else:
            passed = response.relevancy
        blocked = response.nsfw or response.contain_sensitive_info
        retry_count = state.get("retry_count", 0) + 1
        logger.info(
            f"Judge (attempt {retry_count}): passed={passed}, blocked={blocked} | "
            f"faithfulness={response.faithfulness}, relevancy={response.relevancy}, "
            f"hallucination={response.hallucination}"
        )
        if blocked:
            logger.warning(
                f"Answer blocked by judge (nsfw={response.nsfw}, "
                f"sensitive_info={response.contain_sensitive_info})."
            )
        elif not passed:
            logger.warning(f"Answer failed judge: {response.feedback}")
        return {
            "judge_passed": passed,
            "judge_blocked": blocked,
            "feedback": None if passed else response.feedback,
            "retry_count": retry_count,
        }

    return judge_node
