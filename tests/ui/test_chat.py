from types import SimpleNamespace
import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage

from lang_rag_playground.ui.chat import format_citations, format_node_step, respond


def test_format_citations_matches_spec():
    docs = [
        Document(
            page_content="Örneklem 320 kişidir.",
            metadata={"document_name": "tez.pdf", "page": 3, "paragraph_no": 2, "reranker_score": 9.0},
        )
    ]
    assert format_citations(docs) == "[1] tez.pdf, s.3, ¶2 — reranker 9.0"


def test_format_node_step_creates_done_chat_message():
    step = format_node_step("intent", {"intent": "knowledge_question", "intent_confidence": 0.95, "resolved_query": "örneklem sayısı"})
    assert step is not None
    assert "🎯 Niyet: knowledge_question (güven 0.95)" in step.metadata["title"]
    assert step.metadata["status"] == "done"


def test_format_node_step_all_branches():
    s_safe = format_node_step("input_guardrails", {"is_input_safe": True})
    assert s_safe is not None and s_safe.content == "Girdi güvenli."
    s_pii = format_node_step("input_guardrails", {"is_input_safe": True, "messages": ["masked"]})
    assert s_pii is not None and s_pii.content == "Girdi güvenli (PII maskelendi)."
    s_unsafe = format_node_step("input_guardrails", {"is_input_safe": False, "security_message": "Engellendi"})
    assert s_unsafe is not None and s_unsafe.content == "Engellendi"

    s_mem_empty = format_node_step("memory_recall", {"memories": []})
    assert s_mem_empty is not None and s_mem_empty.content == "İlgili hatıra bulunamadı."
    s_mem = format_node_step("memory_recall", {"memories": ["A", "B"]})
    assert s_mem is not None and s_mem.metadata["title"] == "🧠 2 hatıra bulundu"

    s_ret = format_node_step("retrieval", {"raw_documents": [1, 2, 3]})
    assert s_ret is not None and s_ret.metadata["title"] == "🔍 3 belge bulundu"

    s_rerank = format_node_step("reranker", {"reranked_documents": [1, 2]})
    assert s_rerank is not None and s_rerank.metadata["title"] == "📑 2 belge sıralandı"

    s_asst_1 = format_node_step("assistant", {"retry_count": 0, "reranked_documents": []})
    assert s_asst_1 is not None and s_asst_1.metadata["title"] == "✍️ Cevap yazıldı"
    assert s_asst_1.content == "Yanıt üretildi."
    s_asst_2 = format_node_step("assistant", {"retry_count": 1, "reranked_documents": [1]})
    assert s_asst_2 is not None and s_asst_2.metadata["title"] == "✍️ Cevap yeniden yazıldı"
    assert s_asst_2.content == "İncelenen kaynak sayısı: 1"

    s_judge_ok = format_node_step("judge", {"judge_passed": True})
    assert s_judge_ok is not None and s_judge_ok.metadata["title"] == "⚖️ Doğrulama: geçti"
    s_judge_fail = format_node_step("judge", {"judge_passed": False, "feedback": "Hatalı"})
    assert s_judge_fail is not None and s_judge_fail.metadata["title"] == "⚖️ Doğrulama: geçmedi (Hatalı)"

    s_mem_ext = format_node_step("memory_extract", {})
    assert s_mem_ext is not None and s_mem_ext.metadata["title"] == "💾 Hafıza güncellendi"

    assert format_node_step("output_guardrails", {}) is None
    assert format_node_step("blocked", {}) is None


@pytest.mark.asyncio
async def test_respond_streams_steps_unverified_warning_and_citations():
    cited_doc = Document(
        page_content="320 kişi",
        metadata={"document_name": "tez.pdf", "page": 3, "paragraph_no": 2, "reranker_score": 9.0},
    )
    events = [
        {"input_guardrails": {"is_input_safe": True}},
        {"intent": {"intent": "knowledge_question", "intent_confidence": 0.92, "resolved_query": "örneklem"}},
        {"memory_recall": {"memories": ["Kullanıcı yüksek lisans öğrencisi"]}},
        {"assistant": {"generation": "Örneklem 320 kişidir [1].", "reranked_documents": [cited_doc], "cited_documents": [cited_doc]}},
        {"judge": {"judge_passed": False, "judge_blocked": False, "feedback": "Eksik bağlam", "retry_count": 3}},
        {"output_guardrails": {"generation": "Örneklem 320 kişidir [1].", "messages": [AIMessage(content="Örneklem 320 kişidir [1].")]}},
    ]

    async def fake_astream(*args, **kwargs):
        for ev in events:
            yield ev

    services = SimpleNamespace(
        graph=SimpleNamespace(astream=fake_astream),
        mermaid_diagram="graph TD;\n\tinput_guardrails --> intent;",
    )

    outputs = [ item async for item in respond("Örneklem kaç?", [], "u1", "t1", services) ]
    final_history, final_diagram = outputs[-1]
    assert final_history[0].role == "user"
    assert "⚠️ Bu yanıt doğrulanamadı" in final_history[-1].content
    assert "[1] tez.pdf, s.3, ¶2 — reranker 9.0" in final_history[-1].content
    assert "class input_guardrails,intent,memory_recall,assistant,judge,output_guardrails visited;" in final_diagram


@pytest.mark.asyncio
async def test_respond_handles_exception_and_marks_failed_node():
    async def failing_astream(*args, **kwargs):
        yield {"input_guardrails": {"is_input_safe": True}}
        raise RuntimeError("LLM zaman aşımı")

    services = SimpleNamespace(
        graph=SimpleNamespace(astream=failing_astream),
        mermaid_diagram="graph TD;\n\tinput_guardrails --> intent;",
    )

    outputs = [ item async for item in respond("Merhaba", [], "u1", "t1", services) ]
    final_history, final_diagram = outputs[-1]
    assert "Bir hata oluştu: LLM zaman aşımı" in final_history[-1].content
    assert "class input_guardrails failed;" in final_diagram
