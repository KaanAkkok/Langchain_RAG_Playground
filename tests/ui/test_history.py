from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from lang_rag_playground.ui.history import list_threads, load_thread, new_thread_id


def test_new_thread_id_is_unique():
    assert new_thread_id() != new_thread_id()


@pytest.mark.asyncio
async def test_list_threads_deduplicates_and_sorts_newest_first():
    cp1_latest = SimpleNamespace(
        config={"configurable": {"thread_id": "t1"}},
        checkpoint={
            "ts": "2026-11-02T10:05:00Z",
            "channel_values": {
                "messages": [
                    HumanMessage(
                        content="İlk sohbetin oldukça uzun olan başlık metni kırk karakteri geçiyor"
                    ),
                    AIMessage(content="Yanıt 1"),
                ]
            },
        },
    )
    cp1_older = SimpleNamespace(
        config={"configurable": {"thread_id": "t1"}},
        checkpoint={
            "ts": "2026-11-02T10:00:00Z",
            "channel_values": {"messages": [HumanMessage(content="İlk sohbet")]},
        },
    )
    cp2_newest = SimpleNamespace(
        config={"configurable": {"thread_id": "t2"}},
        checkpoint={
            "ts": "2026-11-02T11:00:00Z",
            "channel_values": {
                "messages": [
                    HumanMessage(
                        content=[{"type": "text", "text": "İkinci sohbet sorusu"}]
                    )
                ]
            },
        },
    )

    async def fake_alist(config, filter=None):
        assert filter == {"user_id": "u1"}
        for item in [cp1_latest, cp1_older, cp2_newest]:
            yield item

    checkpointer = MagicMock()
    checkpointer.alist = fake_alist

    threads = await list_threads(checkpointer, "u1")
    assert len(threads) == 2
    assert threads[0][1] == "t2"
    assert threads[0][0] == "İkinci sohbet sorusu"
    assert threads[1][1] == "t1"
    assert len(threads[1][0]) <= 43  # 40 chars + "..."


@pytest.mark.asyncio
async def test_load_thread_converts_human_and_ai_messages():
    graph = MagicMock()
    graph.aget_state = AsyncMock(
        return_value=SimpleNamespace(
            values={
                "messages": [
                    HumanMessage(content="Merhaba"),
                    AIMessage(content="Size nasıl yardımcı olabilirim?"),
                ]
            }
        )
    )
    chat_msgs = await load_thread(graph, "t1")
    assert len(chat_msgs) == 2
    assert chat_msgs[0].role == "user"
    assert chat_msgs[0].content == "Merhaba"
    assert chat_msgs[1].role == "assistant"
    assert chat_msgs[1].content == "Size nasıl yardımcı olabilirim?"
