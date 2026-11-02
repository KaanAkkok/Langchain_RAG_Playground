from langchain_core.messages import AIMessage

from lang_rag_playground.core.logger import get_logger
from lang_rag_playground.guardrails.guardrails import INJECTION_REFUSAL, Guardrails
from lang_rag_playground.models.agent_state_model import AgentState
from lang_rag_playground.nodes.utils import get_user_last_message

logger = get_logger(__name__)


def make_input_guardrails_node(guardrails: Guardrails):
    async def input_guardrails_node(state: AgentState) -> dict:
        last_user_msg = get_user_last_message(state)

        update: dict = {
            "is_input_safe": True,
            "security_message": None,
            "memories": [],
            "raw_documents": [],
            "reranked_documents": [],
            "generation": "",
            "cited_documents": [],
            "judge_passed": False,
            "judge_blocked": False,
            "feedback": None,
            "retry_count": 0,
        }

        result = guardrails.input_guardrail(last_user_msg)
        if not result.is_input_safe:
            update["is_input_safe"] = False
            update["security_message"] = INJECTION_REFUSAL
        elif result.message is not None:
            update["messages"] = [result.message]
        return update

    return input_guardrails_node


def make_output_guardrails_node(guardrails: Guardrails):
    async def output_guardrails_node(state: AgentState) -> dict:
        generated_response = state["generation"]
        if not generated_response:
            raise ValueError("No generated response found in state.")
        safe_response = guardrails.output_guardrail(generated_response)
        if not state.get("judge_passed"):
            logger.warning(
                "Answer could not be verified by the judge. Hallucination or irrelevancy may be present."
            )
        return {
            "generation": safe_response,
            "messages": [AIMessage(content=safe_response)],
        }

    return output_guardrails_node
