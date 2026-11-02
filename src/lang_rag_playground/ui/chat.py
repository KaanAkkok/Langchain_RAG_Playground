from collections.abc import AsyncIterator, Callable, Sequence
from typing import Any

import gradio as gr
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage

from lang_rag_playground.models.context_model import Context
from lang_rag_playground.ui.graph_view import render
from lang_rag_playground.ui.services import AppServices


def format_citations(documents: Sequence[Document]) -> str:
    lines: list[str] = []
    for i, doc in enumerate(documents, start=1):
        doc_name = doc.metadata.get("document_name", "Bilinmeyen")
        page = doc.metadata.get("page", "?")
        para = doc.metadata.get("paragraph_no", "?")
        reranker_score = float(doc.metadata.get("reranker_score") or 0.0)
        if reranker_score > 0:
            score_label = f"reranker {reranker_score:.1f}"
        else:
            score_label = f"hybrid {float(doc.metadata.get('score') or 0.0):.3f} (rerank yok)"
        lines.append(f"[{i}] {doc_name}, page.{page}, paragraph.{para} — {score_label}\n\n{doc.page_content[:200]}...\n")
    return "\n".join(lines)


def _format_input_guardrails(update: dict[str, Any]) -> tuple[str, str]:
    title = "[GUARDRAILS] Girdi kontrolü"
    if not update.get("is_input_safe", True):
        content = update.get("security_message") or "Güvenlik engeli uygulandı."
    elif "messages" in update:
        content = "Girdi güvenli (PII maskelendi)."
    else:
        content = "Girdi güvenli."
    return title, content


def _format_intent(update: dict[str, Any]) -> tuple[str, str]:
    intent = update.get("intent", "unknown")
    conf = float(update.get("intent_confidence", 0.0))
    rq = update.get("resolved_query", "")
    title = f"[INTENT] Niyet: {intent} (güven {conf:.2f})"
    content = f"Çözümlenen sorgu: {rq}" if rq else f"Niyet: {intent}"
    return title, content


def _format_memory_recall(update: dict[str, Any]) -> tuple[str, str]:
    memories = update.get("memories") or []
    title = f"[MEMORY] {len(memories)} hatıra bulundu"
    content = "\n".join(f"- {m}" for m in memories) if memories else "İlgili hatıra bulunamadı."
    return title, content


def _format_retrieval(update: dict[str, Any]) -> tuple[str, str]:
    docs = update.get("raw_documents") or []
    title = f"[RETRIEVAL] {len(docs)} belge bulundu"
    content = f"Qdrant'tan {len(docs)} aday belge getirildi."
    return title, content


def _format_reranker(update: dict[str, Any]) -> tuple[str, str]:
    docs = update.get("reranked_documents") or []
    title = f"[RERANKER] {len(docs)} belge sıralandı"
    content = f"{len(docs)} belge yeniden sıralandı."
    return title, content


def _format_assistant(update: dict[str, Any]) -> tuple[str, str]:
    retry_count = int(update.get("retry_count", 0) or 0)
    reranked = update.get("reranked_documents") or []
    title = f"[ASSISTANT] Cevap yeniden yazıldı" if retry_count > 0 else "✍️ Cevap yazıldı"
    content = f"İncelenen kaynak sayısı: {len(reranked)}" if reranked else "Yanıt üretildi."
    return title, content


def _format_judge(update: dict[str, Any]) -> tuple[str, str]:
    passed = update.get("judge_passed", False)
    feedback = update.get("feedback") or ""
    if passed:
        title = f"[JUDGE] Doğrulama: geçti"
        content = "Yanıt doğrulandı."
    else:
        title = f"[JUDGE] Doğrulama: geçmedi ({feedback})" if feedback else "[JUDGE] Doğrulama: geçmedi"
        content = feedback or "Yanıt doğrulamadan geçemedi."
    return title, content


def _format_memory_extract(_update: dict[str, Any]) -> tuple[str, str]:
    return "[MEMORY] Hafıza güncellendi", "Uzun süreli hafıza güncellendi."


NODE_STEPS: dict[str, Callable[[dict[str, Any]], tuple[str, str]]] = {
    "input_guardrails": _format_input_guardrails,
    "intent": _format_intent,
    "memory_recall": _format_memory_recall,
    "retrieval": _format_retrieval,
    "reranker": _format_reranker,
    "assistant": _format_assistant,
    "judge": _format_judge,
    "memory_extract": _format_memory_extract,
}


def format_node_step(node_name: str, update: dict[str, Any]) -> gr.ChatMessage | None:
    formatter = NODE_STEPS.get(node_name)
    if formatter is None:
        return None
    title, content = formatter(update)
    return gr.ChatMessage(
        role="assistant",
        content=content,
        metadata={"title": title, "status": "done"},
    )


def _extract_final_answer(update: dict[str, Any], accumulated_state: dict[str, Any]) -> str:
    messages = update.get("messages") or []
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            if isinstance(msg.content, str):
                return msg.content
            text_attr = getattr(msg, "text", None)
            if isinstance(text_attr, str):
                return text_attr
    return str(update.get("generation") or accumulated_state.get("generation") or "")


async def respond(
    message: str,
    chat_history: list,
    user_id: str,
    thread_id: str,
    services: AppServices,
    append_user_message: bool = True,
) -> AsyncIterator[tuple[list, str]]:
    history = list(chat_history)
    if append_user_message:
        history.append(gr.ChatMessage(role="user", content=message))
        yield (list(history), render(services.mermaid_diagram))

    visited: list[str] = []
    accumulated_state: dict[str, Any] = {}
    last_node: str | None = None

    try:
        async for event in services.graph.astream(
            {"messages": [HumanMessage(content=message)]},
            config={"configurable": {"thread_id": thread_id}, "metadata": {"user_id": user_id}},
            context=Context(user_id=user_id),
            stream_mode="updates",
        ):
            for node_name, update in event.items():
                last_node = node_name
                if node_name not in visited:
                    visited.append(node_name)
                update_dict = update if isinstance(update, dict) else {}
                if isinstance(update, dict):
                    accumulated_state.update(update)

                step_input = {
                    **({k: accumulated_state[k] for k in ("retry_count",) if k in accumulated_state}),
                    **update_dict,
                }
                step_msg = format_node_step(node_name, step_input)
                if step_msg is not None:
                    history.append(step_msg)

                if node_name in ("output_guardrails", "blocked"):
                    answer_text = _extract_final_answer(update_dict, accumulated_state)
                    if (
                        node_name == "output_guardrails"
                        and accumulated_state.get("judge_passed") is False
                    ):
                        answer_text += "\n\n[WARNING] Bu yanıt doğrulanamadı"
                    if accumulated_state.get("cited_documents"):
                        answer_text += "\n\n**Kaynaklar:**\n" + format_citations(
                            accumulated_state["cited_documents"]
                        )
                    history.append(gr.ChatMessage(role="assistant", content=answer_text))

                yield (
                    list(history),
                    render(services.mermaid_diagram, active_node=node_name, visited=visited),
                )

        yield (
            list(history),
            render(services.mermaid_diagram, active_node=None, visited=visited),
        )
    except Exception as exc:
        history.append(gr.ChatMessage(role="assistant", content=f"❌ Bir hata oluştu: {exc}"))
        yield (
            list(history),
            render(
                services.mermaid_diagram,
                active_node=None,
                visited=visited,
                failed_node=last_node,
            ),
        )
