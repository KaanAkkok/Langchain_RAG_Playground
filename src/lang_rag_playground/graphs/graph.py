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
    make_assistant_node,
)
from lang_rag_playground.nodes.blocked_node import blocked_response_node
from lang_rag_playground.nodes.guardrails_node import (
    make_input_guardrails_node,
    make_output_guardrails_node,
)
from lang_rag_playground.nodes.intent_node import build_intent_chain, make_intent_node
from lang_rag_playground.nodes.judge_node import build_judge_chain, make_judge_node
from lang_rag_playground.nodes.memory_node import (
    build_memory_extract_chain,
    make_memory_extract_node,
    make_memory_recall_node,
)
from lang_rag_playground.nodes.reranker_node import make_reranker_node
from lang_rag_playground.nodes.retrieval_node import make_retrieval_node
from lang_rag_playground.retrieval.reranking import build_reranker_chain
from lang_rag_playground.retrieval.retrieval_service import RetrievalService


def workflow_graph(
    retrieval_service: RetrievalService,
    guardrails_service: Guardrails,
    store: BaseStore | None = None,
    checkpointer: InMemorySaver | None = None,
):
    if any(service is None for service in [retrieval_service, guardrails_service]):
        raise ValueError("Retrieval service and guardrails service must be provided.")

    intent_chain = build_intent_chain()
    reranker_chain = build_reranker_chain()
    assistant_chain = build_assistant_chain()
    judge_chain = build_judge_chain()
    memory_chain = build_memory_extract_chain()

    retry_policy = RetryPolicy(max_attempts=settings.LLM_MAX_ATTEMPTS)

    builder = StateGraph(AgentState, context_schema=Context)
    builder.add_node("input_guardrails", make_input_guardrails_node(guardrails_service))
    builder.add_node(
        "intent", make_intent_node(intent_chain), retry_policy=retry_policy
    )
    builder.add_node(
        "retrieval", make_retrieval_node(retrieval_service), retry_policy=retry_policy
    )
    builder.add_node(
        "reranker", make_reranker_node(reranker_chain), retry_policy=retry_policy
    )
    builder.add_node(
        "assistant",
        make_assistant_node(assistant_chain),
        retry_policy=retry_policy,
    )
    builder.add_node("judge", make_judge_node(judge_chain), retry_policy=retry_policy)
    builder.add_node(
        "output_guardrails", make_output_guardrails_node(guardrails_service)
    )
    builder.add_node("memory_recall", make_memory_recall_node())
    builder.add_node("memory_extract", make_memory_extract_node(memory_chain))
    builder.add_node("blocked", blocked_response_node)

    builder.add_edge(START, "input_guardrails")
    builder.add_edge("intent", "memory_recall")
    builder.add_edge("retrieval", "reranker")
    builder.add_edge("reranker", "assistant")
    builder.add_edge("assistant", "judge")
    builder.add_edge("blocked", END)
    builder.add_edge("memory_extract", END)

    builder.add_conditional_edges("input_guardrails", route_after_input_guardrails)
    builder.add_conditional_edges("memory_recall", route_after_memory_recall)
    builder.add_conditional_edges("output_guardrails", route_after_output_guardrails)
    builder.add_conditional_edges("judge", route_after_judge)

    return builder.compile(checkpointer=checkpointer, store=store)


def agentic_graph(
    retrieval_service: RetrievalService,
    guardrails_service: Guardrails,
    store: BaseStore | None = None,
    checkpointer: InMemorySaver | None = None,
):
    if any(service is None for service in [retrieval_service, guardrails_service]):
        raise ValueError("Retrieval service and guardrails service must be provided.")

    intent_chain = build_intent_chain()
    reranker_chain = build_reranker_chain()
    assistant_agent = build_assistant_agent(retrieval_service, reranker_chain)
    judge_chain = build_judge_chain()
    memory_chain = build_memory_extract_chain()

    retry_policy = RetryPolicy(max_attempts=settings.LLM_MAX_ATTEMPTS)

    builder = StateGraph(AgentState, context_schema=Context)
    builder.add_node("input_guardrails", make_input_guardrails_node(guardrails_service))
    builder.add_node(
        "intent", make_intent_node(intent_chain), retry_policy=retry_policy
    )
    builder.add_node(
        "assistant",
        make_agent_assistant_node(assistant_agent),
        retry_policy=retry_policy,
    )
    builder.add_node("judge", make_judge_node(judge_chain), retry_policy=retry_policy)
    builder.add_node(
        "output_guardrails", make_output_guardrails_node(guardrails_service)
    )
    builder.add_node("memory_recall", make_memory_recall_node())
    builder.add_node("memory_extract", make_memory_extract_node(memory_chain))
    builder.add_node("blocked", blocked_response_node)

    builder.add_edge(START, "input_guardrails")
    builder.add_edge("intent", "memory_recall")
    builder.add_edge("memory_recall", "assistant")
    builder.add_edge("assistant", "judge")
    builder.add_edge("blocked", END)
    builder.add_edge("memory_extract", END)

    builder.add_conditional_edges("input_guardrails", route_after_input_guardrails)
    builder.add_conditional_edges("output_guardrails", route_after_output_guardrails)
    builder.add_conditional_edges("judge", route_after_judge)

    return builder.compile(checkpointer=checkpointer, store=store)


if __name__ == "__main__":
    from langgraph.store.memory import InMemoryStore

    from lang_rag_playground.retrieval.vectordb_service import (
        AsyncQdrantVectorDBService,
    )
    from lang_rag_playground.services.llm import build_embedding_model

    embedding_model = build_embedding_model()
    retrieval_service = RetrievalService(
        AsyncQdrantVectorDBService(embedding_model, host="localhost", port=6333),
        "dummy",
    )
    workflow = workflow_graph(
        retrieval_service, Guardrails(), InMemoryStore(), InMemorySaver()
    )
    workflow.get_graph().draw_mermaid_png(output_file_path="graph_diagram_workflow.png")
    agentic = agentic_graph(
        retrieval_service, Guardrails(), InMemoryStore(), InMemorySaver()
    )
    agentic.get_graph().draw_mermaid_png(output_file_path="graph_diagram_agentic.png")
