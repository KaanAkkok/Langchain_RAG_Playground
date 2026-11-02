from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import gradio as gr
import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage

from lang_rag_playground.ui.app import create_app, handle_submit


def _dummy_services():
    async def fake_astream(*args, **kwargs):
        yield {"input_guardrails": {"is_input_safe": True}}
        yield {
            "output_guardrails": {
                "generation": "Cevap",
                "messages": [AIMessage(content="Cevap")],
                "judge_passed": True,
            }
        }

    async def fake_alist(config, filter=None):
        if False:
            yield None

    extractor = MagicMock()
    extractor.extract.return_value = "PDF içeriği"
    chunker = MagicMock()
    chunker.chunk = AsyncMock(return_value=[Document(page_content="parça 1")])
    retrieval = MagicMock()
    retrieval.store_documents = AsyncMock(return_value=1)

    return SimpleNamespace(
        graph=SimpleNamespace(astream=fake_astream, aget_state=AsyncMock()),
        checkpointer=SimpleNamespace(alist=fake_alist),
        store=MagicMock(),
        retrieval_service=retrieval,
        guardrails=MagicMock(),
        extractor=extractor,
        chunker=chunker,
        mermaid_diagram="graph TD;\n\tinput_guardrails --> output_guardrails;",
    )


@pytest.mark.asyncio
async def test_handle_submit_file_only_ingests_without_calling_graph(tmp_path: Path):
    pdf = tmp_path / "ornek.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    services = _dummy_services()
    services.graph.astream = MagicMock()  # should not be called

    outputs = [
        out
        async for out in handle_submit(
            {"text": "", "files": [str(pdf)]},
            [],
            "u1",
            "t1",
            services,
        )
    ]
    final_history, _, final_textbox, _ = outputs[-1]
    assert any("Qdrant'a yazıldı" in m.content for m in final_history)
    assert final_textbox["interactive"] is True
    services.graph.astream.assert_not_called()


@pytest.mark.asyncio
async def test_handle_submit_file_and_text_ingests_then_streams_answer(tmp_path: Path):
    pdf = tmp_path / "tez.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    services = _dummy_services()

    outputs = [
        out
        async for out in handle_submit(
            {"text": "Bu PDF'te örneklem kaç kişi?", "files": [str(pdf)]},
            [],
            "u1",
            "t1",
            services,
        )
    ]
    final_history, _, final_textbox, _ = outputs[-1]
    assert any("Cevap" in m.content for m in final_history)
    assert final_textbox["interactive"] is True


def test_create_app_builds_gradio_blocks():
    demo = create_app(_dummy_services())
    assert isinstance(demo, gr.Blocks)
