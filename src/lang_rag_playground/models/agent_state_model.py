from typing import Annotated, TypedDict

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Represents the state of the agent during a conversation."""

    messages: Annotated[list[BaseMessage], add_messages] # messages is a list of BaseMessage objects, which can be either HumanMessage or AIMessage
    memories: list[str] # memories is a list of strings representing the agent's memories
    is_input_safe: bool # is_input_safe is a boolean indicating whether the input is safe or not
    security_message: str | None # security_message is a string or None, if input or output is unsafe, the message to be sent to the user
    intent: str # intent is a string representing the extracted intent from the user's input
    intent_confidence: float # intent_confidence is a float representing the confidence score of the extracted intent
    resolved_query: str # resolved_query is a string representing the resolved query after intent extraction
    raw_documents: list[Document] # raw_documents is a list of Document objects representing the raw documents retrieved from the retrieval node
    reranked_documents: list[Document] # reranked_documents is a list of Document objects representing the documents after reranking
    generation: str # generation is a string representing the generated response from the assistant node
    cited_documents: list[Document] # cited_documents is a list of Document objects representing the documents cited in the generated response
    judge_blocked: bool # judge_blocked is a boolean indicating whether the generated response was blocked by the judge node
    judge_passed: bool # judge_passed is a boolean indicating whether the generated response passed the judge node's evaluation
    feedback: str | None # feedback is a string or None, if the generated response was blocked or failed the judge node's evaluation, the feedback to be sent to the user
    retry_count: int # retry_count is an integer representing the number of times the assistant node has been retried after failing the judge node's evaluation
