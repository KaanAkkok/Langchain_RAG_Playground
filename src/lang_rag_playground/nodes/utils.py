from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, HumanMessage, trim_messages

from lang_rag_playground.models.agent_state_model import AgentState


def get_user_last_message(state: AgentState) -> BaseMessage:
    last_user_msg = next(
        (
            message
            for message in reversed(state["messages"])
            if isinstance(message, HumanMessage)
        ),
        None,
    )
    if last_user_msg is None:
        raise ValueError("No user message found in state.")
    return last_user_msg


def trim_history(state: AgentState, max_tokens: int) -> list[BaseMessage]:
    trimmed_history = trim_messages(
        state["messages"],
        strategy="last",
        max_tokens=max_tokens,
        token_counter="approximate",
        start_on="human",
    )
    return trimmed_history


def format_sources(documents: list[Document], start: int = 1) -> str:
    if not documents:
        return "(kaynak yok)"
    return "\n\n".join(
        f"[{i}] ({doc.metadata.get('document_name', '')}, s.{doc.metadata.get('page', '')})\n{doc.page_content}"
        for i, doc in enumerate(documents, start=start)
    )


def format_feedback(feedback: str | None) -> str:
    if not feedback:
        return ""
    return f"\n\n## Önceki cevabın düzeltilmesi gereken yönleri\n{feedback}"
