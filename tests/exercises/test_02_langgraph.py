"""Bölüm 2: LangGraph (Görev 5-7) doğrulama testleri.

Çalıştır: uv run pytest tests/exercises/test_02_langgraph.py -v
Tek görev: uv run pytest tests/exercises/test_02_langgraph.py -v -k gorev6

API anahtarı veya Qdrant gerektirmez; LLM zincirleri ve düğümler sahte nesnelerle değiştirilir.
"""

import asyncio
from typing import Any, cast
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import Runnable, RunnableLambda
from langgraph.checkpoint.memory import InMemorySaver

from lang_rag_playground.graphs import graph as graph_module
from lang_rag_playground.graphs import routers
from lang_rag_playground.nodes import intent_node
from lang_rag_playground.schemas.intent_schema import Intent

YAZILMADI = (
    "Bu görev henüz yazılmadı (NotImplementedError). "
    "Koddaki TODO yorumuna ve Öğrenci Rehberi'ndeki ilgili göreve bak."
)


def _call(fn, *args, **kwargs):
    """Fonksiyonu/düğümü çalıştırır; NotImplementedError ise anlaşılır şekilde kırmızı olur."""
    try:
        result = fn(*args, **kwargs)
        if asyncio.iscoroutine(result):
            result = asyncio.run(result)
        return result
    except NotImplementedError:
        pytest.fail(YAZILMADI, pytrace=False)


# ------------------------------------------------------------- Görev 5: intent
class SahteLLM:
    """build_chat_model yerine geçer; with_structured_output çağrısını kaydeder."""

    def __init__(self, cevap):
        self.cevap = cevap
        self.sema = None
        self.gelen = []

    def with_structured_output(self, sema):
        self.sema = sema

        def _cevap(prompt_value):
            self.gelen.append(prompt_value)
            return self.cevap

        return RunnableLambda(_cevap)


def _sahte_zincir(cevap):
    """ainvoke ile çağrılan, girdiyi kaydeden sahte zincir."""
    gelen = []

    def _f(girdi):
        gelen.append(girdi)
        return cevap

    return RunnableLambda(_f), gelen


def test_gorev5_build_intent_chain(monkeypatch):
    llm = SahteLLM(Intent(intent="chitchat", confidence=0.9, resolved_query="selam"))
    monkeypatch.setattr(intent_node, "build_chat_model", lambda *a, **k: llm)
    zincir = _call(intent_node.build_intent_chain, "model", 0.0)
    assert isinstance(zincir, Runnable), "build_intent_chain bir Runnable (prompt | llm) döndürmeli."
    assert llm.sema is Intent, "llm.with_structured_output(Intent) kullanılmalı."
    sonuc = zincir.invoke({"input_text": "selam", "history": [HumanMessage(content="selam")]})
    assert sonuc.intent == "chitchat" and llm.gelen, (
        "Zincir INTENT_TEMPLATE | llm.with_structured_output(Intent) olmalı."
    )


def test_gorev5_intent_node_yuksek_guven():
    zincir, gelen = _sahte_zincir(
        Intent(intent="knowledge_question", confidence=0.9, resolved_query="çözülmüş soru")
    )
    dugum = intent_node.make_intent_node(zincir, min_confidence=0.6)
    sonuc = _call(dugum, {"messages": [HumanMessage(content="izin kaç gün?")]})
    assert sonuc == {
        "intent": "knowledge_question",
        "intent_confidence": 0.9,
        "resolved_query": "çözülmüş soru",
    }, "intent, intent_confidence ve resolved_query döndürülmeli."
    assert gelen[0]["input_text"] == "izin kaç gün?", "input_text son kullanıcı mesajının metni olmalı."
    assert len(gelen[0].get("history", [])) >= 1, "Kırpılmış geçmiş 'history' ile verilmeli."


def test_gorev5_dusuk_guven_netlestirme():
    zincir, _ = _sahte_zincir(Intent(intent="knowledge_question", confidence=0.3, resolved_query="x"))
    dugum = intent_node.make_intent_node(zincir, min_confidence=0.6)
    sonuc = _call(dugum, {"messages": [HumanMessage(content="bi şey")]})
    assert sonuc["intent"] == "needs_clarification", (
        "confidence < min_confidence ise intent 'needs_clarification' olmalı."
    )
    assert sonuc["intent_confidence"] == 0.3, "Orijinal güven skoru korunmalı."


def test_gorev5_esik_degerinde_degismez():
    zincir, _ = _sahte_zincir(Intent(intent="chitchat", confidence=0.6, resolved_query="x"))
    dugum = intent_node.make_intent_node(zincir, min_confidence=0.6)
    sonuc = _call(dugum, {"messages": [HumanMessage(content="selam")]})
    assert sonuc["intent"] == "chitchat", "confidence == min_confidence için intent değişmemeli (>= kontrolü)."


# ------------------------------------------------------------ Görev 6: router'lar
@pytest.mark.parametrize(
    "state,beklenen",
    [({"is_input_safe": False}, "blocked"), ({}, "blocked"), ({"is_input_safe": True}, "intent")],
)
def test_gorev6_route_after_input_guardrails(state, beklenen):
    assert _call(routers.route_after_input_guardrails, state) == beklenen, (
        "Güvensiz veya bilinmeyen girdi 'blocked', güvenli girdi 'intent' olmalı (state.get kullan)."
    )


@pytest.mark.parametrize(
    "intent,beklenen",
    [("knowledge_question", "retrieval"), ("chitchat", "assistant"), ("", "assistant")],
)
def test_gorev6_route_after_memory_recall(intent, beklenen):
    assert _call(routers.route_after_memory_recall, {"intent": intent}) == beklenen


@pytest.mark.parametrize(
    "state,beklenen,aciklama",
    [
        ({"judge_blocked": True, "judge_passed": True, "retry_count": 0}, "blocked", "judge_blocked her şeyden önce gelir"),
        ({"judge_blocked": False, "judge_passed": True, "retry_count": 1}, "output_guardrails", "geçti"),
        ({"judge_blocked": False, "judge_passed": False, "retry_count": 1}, "assistant", "hak var, yeniden dene"),
        ({"judge_blocked": False, "judge_passed": False, "retry_count": 3}, "output_guardrails", "hak bitti (>=)"),
        ({"judge_blocked": False, "judge_passed": False}, "assistant", "retry_count yoksa 0 say"),
    ],
)
def test_gorev6_route_after_judge(state, beklenen, aciklama):
    assert _call(routers.route_after_judge, state, max_retries=3) == beklenen, aciklama


@pytest.mark.parametrize("adet,beklenen", [(4, "memory_extract"), (3, "__end__")])
def test_gorev6_route_after_output_guardrails(adet, beklenen):
    msgs = [HumanMessage(content="x")] * adet
    assert _call(routers.route_after_output_guardrails, {"messages": msgs}, batch_size=4) == beklenen, (
        "Mesaj sayısı batch_size'ın katı ise 'memory_extract', değilse '__end__'."
    )


# ------------------------------------------------ Görev 7 (ve 10): graph'lar
WORKFLOW_NODES = {
    "input_guardrails", "intent", "retrieval", "reranker", "assistant",
    "judge", "output_guardrails", "memory_recall", "memory_extract", "blocked",
}  # fmt: skip
AGENTIC_NODES = WORKFLOW_NODES - {"retrieval", "reranker"}


@pytest.fixture
def scenario(monkeypatch):
    """Sahte düğümler kurar. `cfg` ile senaryo, `trace` ile ziyaret sırası izlenir."""
    cfg = {"safe": True, "intent": "knowledge_question", "judge": [True]}
    trace: list[str] = []

    def fake(name, update_fn=None):
        async def node(state):
            trace.append(name)
            return update_fn(state) if update_fn else {}

        return node

    def judge_update(state):
        verdicts = cfg["judge"]
        passed = verdicts[min(state.get("retry_count", 0), len(verdicts) - 1)]
        return {
            "judge_passed": passed,
            "judge_blocked": cfg.get("blocked", False),
            "retry_count": state.get("retry_count", 0) + 1,
        }

    gm = graph_module
    for chain_builder in (
        "build_intent_chain", "build_reranker_chain", "build_assistant_chain",
        "build_judge_chain", "build_memory_extract_chain", "build_assistant_agent",
    ):  # fmt: skip
        monkeypatch.setattr(gm, chain_builder, lambda *a, **k: MagicMock())
    monkeypatch.setattr(
        gm, "make_input_guardrails_node",
        lambda *_: fake("input_guardrails", lambda s: {"is_input_safe": cfg["safe"], "retry_count": 0}),
    )  # fmt: skip
    monkeypatch.setattr(gm, "make_intent_node", lambda *_: fake("intent", lambda s: {"intent": cfg["intent"]}))
    monkeypatch.setattr(gm, "make_retrieval_node", lambda *_: fake("retrieval"))
    monkeypatch.setattr(gm, "make_reranker_node", lambda *_: fake("reranker"))
    monkeypatch.setattr(gm, "make_assistant_node", lambda *_: fake("assistant"))
    monkeypatch.setattr(gm, "make_agent_assistant_node", lambda *_: fake("assistant"))
    monkeypatch.setattr(gm, "make_judge_node", lambda *_: fake("judge", judge_update))
    monkeypatch.setattr(
        gm, "make_output_guardrails_node",
        lambda *_: fake("output_guardrails", lambda s: {"messages": [AIMessage(content="final")]}),
    )  # fmt: skip
    monkeypatch.setattr(gm, "make_memory_recall_node", lambda *a, **k: fake("memory_recall"))
    monkeypatch.setattr(gm, "make_memory_extract_node", lambda *_: fake("memory_extract"))
    monkeypatch.setattr(gm, "blocked_response_node", fake("blocked"))
    return cfg, trace


def build_graph(kind):
    fn = graph_module.workflow_graph if kind == "workflow" else graph_module.agentic_graph
    return _call(fn, MagicMock(), MagicMock(), None, InMemorySaver())


def run_graph(graph, text="merhaba"):
    return asyncio.run(
        graph.ainvoke(
            {"messages": [HumanMessage(content=text)]},
            config={"configurable": {"thread_id": "t1"}},
            context=graph_module.Context(user_id="u1"),
        )
    )


def test_gorev7_dugumler(scenario):
    names = set(build_graph("workflow").get_graph().nodes) - {"__start__", "__end__"}
    assert names == WORKFLOW_NODES, (
        f"workflow_graph düğümleri hatalı. Eksik: {sorted(WORKFLOW_NODES - names)}, "
        f"fazla: {sorted(names - WORKFLOW_NODES)}"
    )


def test_gorev7_bilgi_sorusu_akisi(scenario):
    _, trace = scenario
    run_graph(build_graph("workflow"))
    assert trace == [
        "input_guardrails", "intent", "memory_recall", "retrieval", "reranker",
        "assistant", "judge", "output_guardrails",
    ], f"Workflow akışı beklenenden farklı: {trace}"  # fmt: skip


def test_gorev7_sohbet_retrieval_atlar(scenario):
    cfg, trace = scenario
    cfg["intent"] = "chitchat"
    run_graph(build_graph("workflow"))
    assert "retrieval" not in trace and "reranker" not in trace, (
        "knowledge_question olmayan niyette retrieval/reranker atlanmalı."
    )


def test_gorev7_guvensiz_girdi_blocked(scenario):
    cfg, trace = scenario
    cfg["safe"] = False
    run_graph(build_graph("workflow"))
    assert trace == ["input_guardrails", "blocked"], (
        f"Güvensiz girdide akış input_guardrails -> blocked -> END olmalı: {trace}"
    )


def test_gorev7_judge_kalinca_asistana_doner(scenario):
    cfg, trace = scenario
    cfg["judge"] = [False, True]
    run_graph(build_graph("workflow"))
    assert trace.count("assistant") == 2 and trace.count("retrieval") == 1, (
        f"Judge başarısız olunca retrieval'a değil doğrudan assistant'a dönülmeli: {trace}"
    )
    assert trace[-1] == "output_guardrails"


def test_gorev7_judge_engellerse_blocked(scenario):
    cfg, trace = scenario
    cfg["judge"] = [False]
    cfg["blocked"] = True
    run_graph(build_graph("workflow"))
    assert trace[-2:] == ["judge", "blocked"], f"judge_blocked -> blocked olmalı: {trace}"


def test_gorev7_hafiza_cikarma_kenari(scenario, monkeypatch):
    _, trace = scenario
    monkeypatch.setattr(
        graph_module,
        "route_after_output_guardrails",
        lambda s: routers.route_after_output_guardrails(s, batch_size=2),
    )
    run_graph(build_graph("workflow"))
    # 1 insan + 1 AI mesajı = 2 -> memory_extract çalışmalı
    assert trace[-1] == "memory_extract", (
        f"output_guardrails sonrası koşullu kenar router'a bağlanmalı: {trace}"
    )


def test_gorev7_servis_dogrulamasi_hazir(scenario):
    with pytest.raises(ValueError):
        graph_module.workflow_graph(cast(Any, None), MagicMock())
