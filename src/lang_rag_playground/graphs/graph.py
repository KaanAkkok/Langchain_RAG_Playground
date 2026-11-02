from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.store.base import BaseStore
from langgraph.types import RetryPolicy

from lang_rag_playground.core.settings import settings

from lang_rag_playground.graphs.routers import (
    route_after_input_guardrails,
    route_after_judge,
    route_after_memory_recall,
    route_after_output_guardrails,
)
from lang_rag_playground.guardrails.guardrails import Guardrails
from lang_rag_playground.models.agent_state_model import AgentState
from lang_rag_playground.models.context_model import Context
from lang_rag_playground.nodes.assistant_node import (
    build_assistant_agent,
    build_assistant_chain,
    make_agent_assistant_node,
    make_workflow_assistant_node,
)
from lang_rag_playground.nodes.blocked_node import blocked_response_node
from lang_rag_playground.nodes.guardrails_node import (
    make_input_guardrails_node,
    make_output_guardrails_node,
)
from lang_rag_playground.nodes.intent_node import build_intent_chain, make_intent_node
from lang_rag_playground.nodes.judge_node import build_judge_chain, make_judge_node
from lang_rag_playground.nodes.memory_node import build_memory_extract_chain, make_memory_extract_node, make_memory_recall_node
from lang_rag_playground.nodes.reranker_node import make_reranker_node
from lang_rag_playground.nodes.retrieval_node import make_retrieval_node
from lang_rag_playground.retrieval.reranking import build_reranker_chain
from lang_rag_playground.retrieval.retrieval_service import RetrievalService


def _validate_services(
    retrieval_service: RetrievalService,
    guardrails_service: Guardrails,
    store: BaseStore,
    checkpointer: InMemorySaver | None,
) -> None:
    if any(
        service is None
        for service in [retrieval_service, guardrails_service, store]
    ):
        raise ValueError("Retrieval service, guardrails service, and store must be provided.")
    if checkpointer is None:
        raise ValueError("Checkpointer must be provided.")


def _build_common_graph(
    guardrails_service: Guardrails, retry_policy: RetryPolicy
) -> StateGraph[AgentState, Context, AgentState, AgentState]:
    """Nodes and edges shared by both graphs. The caller adds `assistant` and wires
    `memory_recall` -> ... -> `assistant`."""
    builder = StateGraph(AgentState, context_schema=Context)
    builder.add_node("input_guardrails", make_input_guardrails_node(guardrails_service))
    builder.add_node("intent", make_intent_node(build_intent_chain()), retry_policy=retry_policy)
    builder.add_node("memory_recall", make_memory_recall_node())
    builder.add_node("judge", make_judge_node(build_judge_chain()), retry_policy=retry_policy)
    builder.add_node("output_guardrails", make_output_guardrails_node(guardrails_service))
    builder.add_node("memory_extract", make_memory_extract_node(build_memory_extract_chain()))
    builder.add_node("blocked", blocked_response_node)

    builder.add_edge(START, "input_guardrails")
    builder.add_edge("intent", "memory_recall")
    builder.add_edge("assistant", "judge")
    builder.add_edge("blocked", END)
    builder.add_edge("memory_extract", END)

    builder.add_conditional_edges("input_guardrails", route_after_input_guardrails)
    builder.add_conditional_edges("judge", route_after_judge)
    builder.add_conditional_edges("output_guardrails", route_after_output_guardrails)
    return builder


def workflow_graph(
    retrieval_service: RetrievalService,
    guardrails_service: Guardrails,
    store: BaseStore,
    checkpointer: InMemorySaver | None
):
    """Classic workflow RAG: the graph decides when to search.

    memory_recall ─┬→ retrieval → reranker → assistant → judge
                   └→ assistant (non-knowledge intents)
    """
    _validate_services(retrieval_service, guardrails_service, store, checkpointer)
    retry_policy = RetryPolicy(max_attempts=settings.LLM_MAX_ATTEMPTS)

    builder = _build_common_graph(guardrails_service, retry_policy)
    builder.add_node("retrieval", make_retrieval_node(retrieval_service), retry_policy=retry_policy)
    builder.add_node("reranker", make_reranker_node(build_reranker_chain()), retry_policy=retry_policy)
    builder.add_node("assistant", make_workflow_assistant_node(build_assistant_chain()), retry_policy=retry_policy)

    builder.add_conditional_edges("memory_recall", route_after_memory_recall)
    builder.add_edge("retrieval", "reranker")
    builder.add_edge("reranker", "assistant")

    return builder.compile(checkpointer=checkpointer, store=store)


def agentic_graph(
    retrieval_service: RetrievalService,
    guardrails_service: Guardrails,
    store: BaseStore,
    checkpointer: InMemorySaver | None
):
    """Agentic RAG: the assistant agent decides when and what to search through tools.

    memory_recall → assistant (create_agent ⟲ search_documents) → judge
    """
    _validate_services(retrieval_service, guardrails_service, store, checkpointer)
    retry_policy = RetryPolicy(max_attempts=settings.LLM_MAX_ATTEMPTS)

    assistant_agent = build_assistant_agent(retrieval_service, build_reranker_chain())

    builder = _build_common_graph(guardrails_service, retry_policy)
    builder.add_node("assistant", make_agent_assistant_node(assistant_agent), retry_policy=retry_policy)

    builder.add_edge("memory_recall", "assistant")

    return builder.compile(checkpointer=checkpointer, store=store)


def build_graph(
    retrieval_service: RetrievalService,
    guardrails_service: Guardrails,
    store: BaseStore,
    checkpointer: InMemorySaver | None,
    mode: str = settings.GRAPH_MODE,
):
    graph_factory = {"workflow": workflow_graph, "agentic": agentic_graph}.get(mode)
    if graph_factory is None:
        raise ValueError(f"Unknown graph mode: {mode!r}. Expected 'workflow' or 'agentic'.")
    return graph_factory(retrieval_service, guardrails_service, store, checkpointer)


if __name__ == "__main__":
    from langgraph.store.memory import InMemoryStore

    from lang_rag_playground.retrieval.vectordb_service import AsyncQdrantVectorDBService
    from lang_rag_playground.services.llm import build_embedding_model

    embedding_model = build_embedding_model()
    retrieval_service = RetrievalService(AsyncQdrantVectorDBService(embedding_model, host="localhost", port=6333), "dummy")
    for mode in ("workflow", "agentic"):
        graph = build_graph(retrieval_service, Guardrails(), InMemoryStore(), InMemorySaver(), mode=mode)
        graph.get_graph().draw_mermaid_png(output_file_path=f"graph_diagram_{mode}.png")
