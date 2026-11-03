import uuid
from typing import Any

import gradio as gr
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver


def _extract_text(msg: BaseMessage) -> str:
    """Mesaj içeriğinden güvenli bir şekilde düz metin çıkarır."""
    text_attr = getattr(msg, "text", None)
    if isinstance(text_attr, str) and text_attr.strip():
        return text_attr.strip()
    content = getattr(msg, "content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "".join(parts).strip()
    return str(content).strip()


def new_thread_id() -> str:
    """Yeni bir sohbet oturumu için benzersiz UUID4 dizgesi üretir."""
    return str(uuid.uuid4())


async def list_threads(
    checkpointer: InMemorySaver, user_id: str
) -> list[tuple[str, str]]:
    """Kullanıcının sohbet geçmişini en yeniden en eskiye doğru (başlık, thread_id) olarak listeler."""
    latest_by_thread: dict[str, tuple[str, dict[str, Any]]] = {}

    async for item in checkpointer.alist(None, filter={"user_id": user_id}):
        config = getattr(item, "config", None) or {}
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            continue

        checkpoint = getattr(item, "checkpoint", None) or {}
        ts = str(checkpoint.get("ts", ""))

        if thread_id not in latest_by_thread or ts > latest_by_thread[thread_id][0]:
            latest_by_thread[thread_id] = (ts, checkpoint)

    sorted_threads = sorted(
        latest_by_thread.items(),
        key=lambda kv: kv[1][0],
        reverse=True,
    )

    result: list[tuple[str, str]] = []
    for thread_id, (_ts, checkpoint) in sorted_threads:
        messages = checkpoint.get("channel_values", {}).get("messages", [])
        title = "Yeni Sohbet"
        for msg in messages:
            if isinstance(msg, HumanMessage):
                extracted = _extract_text(msg)
                if extracted:
                    title = extracted[:40] + "..." if len(extracted) > 40 else extracted
                break
        result.append((title, thread_id))

    return result


async def load_thread(graph: Any, thread_id: str) -> list[gr.ChatMessage]:
    """Belirtilen thread_id'ye ait mesajları yükleyip Gradio ChatMessage listesine dönüştürür."""
    state = await graph.aget_state({"configurable": {"thread_id": thread_id}})
    messages = (
        (getattr(state, "values", None) or {}).get("messages", []) if state else []
    )

    chat_messages: list[gr.ChatMessage] = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            chat_messages.append(
                gr.ChatMessage(role="user", content=_extract_text(msg))
            )
        elif isinstance(msg, AIMessage):
            text = _extract_text(msg)
            if text:
                chat_messages.append(gr.ChatMessage(role="assistant", content=text))

    return chat_messages
