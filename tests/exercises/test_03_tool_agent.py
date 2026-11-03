"""Bölüm 3: Tool ve Agent (Görev 8-10) doğrulama testleri.

Çalıştır: uv run pytest tests/exercises/test_03_tool_agent.py -v
Tek görev: uv run pytest tests/exercises/test_03_tool_agent.py -v -k gorev8

API anahtarı veya Qdrant gerektirmez; retrieval servisi, reranker, LLM ve agent sahte nesnelerdir.
"""

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain.agents.middleware import ToolCallLimitMiddleware, ToolRetryMiddleware
from langchain.agents.structured_output import ToolStrategy
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableLambda
from langgraph.errors import GraphRecursionError
from test_02_langgraph import AGENTIC_NODES, build_graph, run_graph, scenario  # noqa: F401

from lang_rag_playground.core.exceptions import RerankerError
from lang_rag_playground.core.settings import settings
from lang_rag_playground.models.agent_context_model import AgentContext
from lang_rag_playground.nodes import assistant_node
from lang_rag_playground.nodes.assistant_node import (
    NOT_FOUND_ANSWER,
    build_assistant_agent,
    make_agent_assistant_node,
)
from lang_rag_playground.schemas.assistant_schema import AssistantResponse
from lang_rag_playground.schemas.reranker_schema import RerankItem, RerankResponse
from lang_rag_playground.tools import retrieve_tool
from lang_rag_playground.tools.retrieve_tool import make_search_documents_tool

YAZILMADI = (
    "Bu görev henüz yazılmadı (NotImplementedError). "
    "Koddaki TODO yorumuna ve Öğrenci Rehberi'ndeki ilgili göreve bak."
)


def _guard(fn):
    try:
        return fn()
    except NotImplementedError:
        pytest.fail(YAZILMADI, pytrace=False)


async def _aguard(coro):
    try:
        return await coro
    except NotImplementedError:
        pytest.fail(YAZILMADI, pytrace=False)


def _docs(n: int, prefix: str = "icerik") -> list[Document]:
    return [
        Document(page_content=f"{prefix} {i}", metadata={"document_name": "tez.pdf", "page": i + 1})
        for i in range(n)
    ]


# ------------------------------------------------- Görev 8: search_documents
def _retrieval(docs: list[Document]) -> AsyncMock:
    service = AsyncMock()
    service.search = AsyncMock(return_value=docs)
    return service


def _reranker(scores: dict[int, float]):
    """id -> skor eşlemesini RerankResponse olarak döndüren sahte zincir."""
    response = RerankResponse(scores=[RerankItem(id=i, score=s) for i, s in scores.items()])
    return RunnableLambda(lambda _: response)


def _failing_reranker():
    def _boom(_):
        raise RerankerError("sahte hata")

    return RunnableLambda(_boom)


def _runtime(context: AgentContext | None = None):
    return SimpleNamespace(context=context if context is not None else AgentContext())


async def _tool(tool, query: str, runtime):
    """@tool ile sarılmış ham async fonksiyonu doğrudan çağırır (ToolRuntime yerine sahte runtime)."""
    return await _aguard(tool.coroutine(query=query, runtime=runtime))


async def test_gorev8_bos_sorgu_hazir_kisim():
    service = _retrieval(_docs(2))
    got = await _tool(make_search_documents_tool(service, _reranker({0: 9})), "   ", _runtime())
    assert got == retrieve_tool.NOT_FOUND_ANSWER
    service.search.assert_not_awaited()


async def test_gorev8_aday_sayisi_candidates():
    service = _retrieval(_docs(3))
    tool = make_search_documents_tool(service, _reranker({0: 9}), candidates=7, top_k=2)
    await _tool(tool, "yapay zeka", _runtime())
    kwargs = service.search.await_args.kwargs
    assert kwargs.get("query") == "yapay zeka", "retrieval_service.search(query=query, ...) şeklinde çağır."
    assert kwargs.get("top_k") == 7, "Aday sayısı için top_k=candidates kullanmalısın, top_k değil."


async def test_gorev8_aday_yoksa_not_found():
    ctx = AgentContext()
    got = await _tool(make_search_documents_tool(_retrieval([]), _reranker({})), "soru", _runtime(ctx))
    assert got == retrieve_tool.NOT_FOUND_ANSWER and ctx.sources == [], (
        "Aday yoksa NOT_FOUND_ANSWER dönmeli ve context.sources boş kalmalı."
    )


async def test_gorev8_rerank_sirasi_ve_esik():
    tool = make_search_documents_tool(
        _retrieval(_docs(3)), _reranker({0: 5.0, 1: 1.0, 2: 9.0}), top_k=5, min_score=3.0
    )
    ctx = AgentContext()
    await _tool(tool, "soru", _runtime(ctx))
    got = [d.page_content for d in ctx.sources]
    assert got == ["icerik 2", "icerik 0"], (
        f"rerank_documents sonucu kullanılmalı (skora göre sıralı, eşik altı elenmiş). Gelen: {got}"
    )


async def test_gorev8_hicbiri_esigi_gecmezse_not_found():
    tool = make_search_documents_tool(_retrieval(_docs(2)), _reranker({0: 1.0, 1: 2.0}), min_score=3.0)
    got = await _tool(tool, "soru", _runtime())
    assert got == retrieve_tool.NOT_FOUND_ANSWER, "Hiç belge eşiği geçmezse NOT_FOUND_ANSWER dönmeli."


async def test_gorev8_reranker_hatasinda_fallback():
    tool = make_search_documents_tool(_retrieval(_docs(5)), _failing_reranker(), top_k=2)
    ctx = AgentContext()
    got = await _tool(tool, "soru", _runtime(ctx))
    assert [d.page_content for d in ctx.sources] == ["icerik 0", "icerik 1"], (
        "RerankerError olursa candidate_docs[:top_k] ile devam etmelisin."
    )
    assert got.startswith("Bulunan kaynaklar:"), "Fallback'te de kaynaklar dönmeli."


async def test_gorev8_cikti_formati():
    tool = make_search_documents_tool(_retrieval(_docs(2)), _reranker({0: 9.0, 1: 8.0}))
    got = await _tool(tool, "soru", _runtime())
    assert got.startswith("Bulunan kaynaklar:\n\n"), (
        "Çıktı 'Bulunan kaynaklar:' + boş satır + format_sources(...) olmalı."
    )
    assert "[1] (tez.pdf, s.1)" in got and "[2] (tez.pdf, s.2)" in got, (
        f"Kaynaklar 1'den başlayarak numaralanmalı. Gelen:\n{got}"
    )


async def test_gorev8_ikinci_cagri_numaralandirmaya_devam_eder():
    ctx = AgentContext()
    first = make_search_documents_tool(_retrieval(_docs(2, "ilk")), _reranker({0: 9.0, 1: 8.0}))
    second = make_search_documents_tool(_retrieval(_docs(1, "ikinci")), _reranker({0: 9.0}))
    await _tool(first, "soru bir", _runtime(ctx))
    got = await _tool(second, "soru iki", _runtime(ctx))
    assert "[3]" in got and "[1]" not in got, (
        f"İkinci aramada numara 3'ten devam etmeli (start = len(sources) + 1). Gelen:\n{got}"
    )
    assert [d.page_content for d in ctx.sources] == ["ilk 0", "ilk 1", "ikinci 0"], (
        "İki aramanın kaynakları aynı context'te birikmeli (extend)."
    )


# ---------------------------------------------- Görev 9: build_assistant_agent
def _build_agent():
    captured = {}

    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return MagicMock()

    fake_llm = MagicMock()
    with patch.object(assistant_node, "build_chat_model", return_value=fake_llm), patch.object(
        assistant_node, "create_agent", side_effect=fake_create_agent
    ):
        _guard(lambda: build_assistant_agent(MagicMock(), MagicMock()))
    assert captured, "create_agent(...) anahtar kelime argümanlarıyla çağrılmalı."
    return captured, fake_llm


def test_gorev9_model_ve_araclar():
    captured, fake_llm = _build_agent()
    assert captured.get("model") is fake_llm, "model=build_chat_model(...) sonucu olmalı."
    names = sorted(t.name for t in captured.get("tools", []))
    assert names == sorted([assistant_node.SEARCH_TOOL_NAME, assistant_node.DATE_TOOL_NAME]), (
        f"Araçlar search_documents ve tarih aracı olmalı. Gelen: {names}"
    )


def test_gorev9_yapilandirilmis_cikti_ve_context():
    captured, _ = _build_agent()
    fmt = captured.get("response_format")
    assert isinstance(fmt, ToolStrategy) and fmt.schema is AssistantResponse, (
        "response_format=ToolStrategy(AssistantResponse) olmalı."
    )
    assert captured.get("context_schema") is AgentContext, "context_schema=AgentContext olmalı."


def test_gorev9_middleware_degerleri():
    captured, _ = _build_agent()
    middleware = list(captured.get("middleware") or [])
    limits = {m.tool_name: m.run_limit for m in middleware if isinstance(m, ToolCallLimitMiddleware)}
    assert limits == {
        assistant_node.SEARCH_TOOL_NAME: settings.MAX_TOOL_CALLS,
        assistant_node.DATE_TOOL_NAME: settings.MAX_TOOL_CALLS,
    }, f"Her araç için run_limit=settings.MAX_TOOL_CALLS olan bir ToolCallLimitMiddleware olmalı. Gelen: {limits}"
    retries = [m for m in middleware if isinstance(m, ToolRetryMiddleware)]
    assert len(retries) == 1, "Bir adet ToolRetryMiddleware olmalı."
    assert retries[0].max_retries == settings.TOOL_MAX_RETRIES, "max_retries=settings.TOOL_MAX_RETRIES olmalı."
    assert retries[0].on_failure is assistant_node._search_tool_failure_message, (
        "on_failure=_search_tool_failure_message olmalı."
    )


# ------------------------------------- Görev 10: agent düğümü + agentic_graph
def _state(**extra) -> Any:
    state = {
        "messages": [HumanMessage("Tezin konusu ne?")],
        "intent": "knowledge_question",
        "memories": [],
        "resolved_query": "tezin konusu",
        "feedback": None,
        "retry_count": 0,
    }
    state.update(extra)
    return state


def _fake_agent(result=None, docs: list[Document] | None = None, error=None):
    """Çağrıldığında context.sources'a belge ekleyen (aracın yaptığı gibi) sahte agent."""
    agent = MagicMock()

    async def ainvoke(inputs, context=None, **_):
        agent.seen_inputs = inputs
        agent.seen_context = context
        if error is not None:
            raise error
        if docs and context is not None:
            context.sources.extend(docs)
        return result

    agent.ainvoke = AsyncMock(side_effect=ainvoke)
    return agent


def _structured(answer: str, cited: list[int]) -> dict:
    return {"structured_response": AssistantResponse(answer=answer, cited_sources=cited), "messages": []}


async def test_gorev10_agent_mesaj_ve_context_ile_cagrilir():
    docs = _docs(2)
    agent = _fake_agent(_structured("cevap [2]", [2]), docs=docs)
    got = await _aguard(make_agent_assistant_node(agent)(_state()))
    assert isinstance(agent.seen_context, AgentContext), (
        "agent.ainvoke(..., context=AgentContext()) şeklinde boş bir AgentContext verilmeli."
    )
    messages = agent.seen_inputs.get("messages")
    assert messages and isinstance(messages[0], SystemMessage), (
        'Girdi {"messages": AGENT_ASSISTANT_TEMPLATE.format_messages(...)} olmalı.'
    )
    assert "tezin konusu" in messages[0].text, (
        "Sistem mesajında resolved_query yer almalı (format_messages'a resolved_query ver)."
    )
    assert got["reranked_documents"] == docs, (
        "reranked_documents, aracın context.sources'a biriktirdiği belgeler olmalı."
    )
    assert got["cited_documents"] == [docs[1]] and got["generation"] == "cevap [2]", (
        "Sonuç _assistant_update(response, agent_context.sources) ile döndürülmeli."
    )


async def test_gorev10_her_cagrida_yeni_context():
    node = make_agent_assistant_node(_fake_agent(_structured("x", []), docs=_docs(1)))
    first = await _aguard(node(_state()))
    second = await _aguard(node(_state()))
    assert len(first["reranked_documents"]) == 1 and len(second["reranked_documents"]) == 1, (
        "Her düğüm çağrısında yeni bir AgentContext() oluşturulmalı; kaynaklar turlar arasında birikmemeli."
    )


async def test_gorev10_duz_metin_cevap():
    got = await _aguard(make_agent_assistant_node(_fake_agent({"messages": [AIMessage("düz cevap")]}))(_state()))
    assert got["generation"] == "düz cevap" and got["cited_documents"] == []


async def test_gorev10_recursion_limitinde_not_found():
    agent = _fake_agent(error=GraphRecursionError("limit"))
    got = await _aguard(make_agent_assistant_node(agent)(_state()))
    assert got["generation"] == NOT_FOUND_ANSWER, (
        "GraphRecursionError durumunda NOT_FOUND_ANSWER dönmeli (hazır kısım; "
        "agent_context try'dan önce oluşturulmalı)."
    )


def test_gorev10_agentic_graph_dugumleri(scenario):
    names = set(build_graph("agentic").get_graph().nodes) - {"__start__", "__end__"}
    assert names == AGENTIC_NODES, (
        f"agentic_graph düğümleri hatalı (retrieval/reranker olmamalı). "
        f"Eksik: {sorted(AGENTIC_NODES - names)}, fazla: {sorted(names - AGENTIC_NODES)}"
    )


def test_gorev10_agentic_akis(scenario):
    _, trace = scenario
    run_graph(build_graph("agentic"))
    assert trace == [
        "input_guardrails", "intent", "memory_recall", "assistant", "judge", "output_guardrails",
    ], f"Agentic akış (memory_recall -> assistant sabit kenar) beklenenden farklı: {trace}"


def test_gorev10_agentic_guvensiz_girdi(scenario):
    cfg, trace = scenario
    cfg["safe"] = False
    run_graph(build_graph("agentic"))
    assert trace == ["input_guardrails", "blocked"], f"Güvensiz girdide blocked'a gidilmeli: {trace}"
