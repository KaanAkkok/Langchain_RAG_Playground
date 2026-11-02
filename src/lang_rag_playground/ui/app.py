from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

import gradio as gr

from lang_rag_playground.ui.chat import respond
from lang_rag_playground.ui.graph_view import render
from lang_rag_playground.ui.history import list_threads, load_thread, new_thread_id
from lang_rag_playground.ui.ingestion import ingest_files
from lang_rag_playground.ui.services import AppServices, build_app_services
from lang_rag_playground.core.settings import settings

APP_CSS = """
#graph-diagram .nodeLabel,
#graph-diagram .nodeLabel * {
    color: #111827 !important;
}
#graph-diagram .node text {
    fill: #111827 !important;
}
"""


async def handle_submit(
    user_input: dict[str, Any] | None,
    chat_history: list[Any],
    user_id: str,
    thread_id: str,
    services: AppServices,
) -> AsyncIterator[tuple[list[Any], str, dict[str, Any], dict[str, Any]]]:
    history = list(chat_history)
    text = ((user_input or {}).get("text") or "").strip()
    raw_files = (user_input or {}).get("files") or []
    files = [
        str(f["path"]) if isinstance(f, dict) and "path" in f else str(f)
        for f in raw_files
    ]
    current_diagram = render(services.mermaid_diagram)

    try:
        if not text and not files:
            return

        if text:
            history.append(gr.ChatMessage(role="user", content=text))

        yield (
            list(history),
            current_diagram,
            gr.update(value=None, interactive=False),
            gr.update(),
        )

        if files:
            history.append(
                gr.ChatMessage(
                    role="assistant",
                    content="Dosyalar işleniyor...",
                    metadata={"title": "[INGESTION] PDF Yükleme", "status": "pending"},
                )
            )
            ingest_idx = len(history) - 1
            ingest_logs: list[str] = []

            async for status_line in ingest_files(
                files,
                services.extractor,
                services.chunker,
                services.retrieval_service,
            ):
                ingest_logs.append(status_line)
                history[ingest_idx] = gr.ChatMessage(
                    role="assistant",
                    content="\n".join(ingest_logs),
                    metadata={"title": "[INGESTION] PDF Yükleme", "status": "pending"},
                )
                yield (
                    list(history),
                    current_diagram,
                    gr.update(interactive=False),
                    gr.update(),
                )

            history[ingest_idx] = gr.ChatMessage(
                role="assistant",
                content="\n".join(ingest_logs),
                metadata={"title": "[INGESTION] PDF Yükleme", "status": "done"},
            )
            yield (
                list(history),
                current_diagram,
                gr.update(interactive=False),
                gr.update(),
            )

        if text:
            async for updated_history, updated_diagram in respond(
                text,
                history,
                user_id,
                thread_id,
                services,
                append_user_message=False,
            ):
                history = updated_history
                current_diagram = updated_diagram
                yield (
                    list(history),
                    current_diagram,
                    gr.update(interactive=False),
                    gr.update(),
                )
    finally:
        if text or files:
            choices = await list_threads(services.checkpointer, user_id)
            radio_update = (
                gr.update(choices=choices, value=thread_id)
                if any(tid == thread_id for _, tid in choices)
                else gr.update(choices=choices)
            )
        else:
            radio_update = gr.update()

        yield (
            list(history),
            current_diagram,
            gr.update(value=None, interactive=True),
            radio_update,
        )


def create_app(services: AppServices | None = None) -> gr.Blocks:
    if services is None:
        services = build_app_services()

    with gr.Blocks(title="Agentic RAG Playground", fill_height=True) as demo:
        user_id_state = gr.State(lambda: str(uuid4()))
        thread_id_state = gr.State(new_thread_id)

        with gr.Sidebar():
            new_chat_btn = gr.Button("+ Yeni Sohbet", variant="primary")
            thread_radio = gr.Radio(
                label="Geçmiş Sohbetler",
                choices=[],
                interactive=True,
            )

        with gr.Row(scale=1, equal_height=True):
            with gr.Column(scale=1):
                diagram_md = gr.Markdown(
                    value=render(services.mermaid_diagram),
                    elem_id="graph-diagram",
                    max_height="85vh",
                )
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(label="Sohbet", scale=1)
                chat_input = gr.MultimodalTextbox(
                    file_types=[".pdf"],
                    file_count="multiple",
                    placeholder="Mesajınızı yazın veya PDF yükleyin...",
                    show_label=False,
                    scale=0,
                    max_lines=5,
                )

        async def _on_submit(
            user_input: dict[str, Any] | None,
            chat_history: list[Any],
            user_id: str,
            thread_id: str,
        ) -> AsyncIterator[tuple[list[Any], str, dict[str, Any], dict[str, Any]]]:
            async for out in handle_submit(
                user_input, chat_history, user_id, thread_id, services
            ):
                yield out

        def _on_new_chat() -> tuple[str, list[Any], str, dict[str, Any]]:
            return (
                new_thread_id(),
                [],
                render(services.mermaid_diagram),
                gr.update(value=None),
            )

        async def _on_select_thread(
            selected_thread_id: str | None,
        ) -> tuple[Any, Any, Any]:
            if not selected_thread_id:
                return gr.update(), gr.update(), gr.update()
            messages = await load_thread(services.graph, selected_thread_id)
            return (
                selected_thread_id,
                messages,
                render(services.mermaid_diagram),
            )

        chat_input.submit(
            fn=_on_submit,
            inputs=[chat_input, chatbot, user_id_state, thread_id_state],
            outputs=[chatbot, diagram_md, chat_input, thread_radio],
        )

        new_chat_btn.click(
            fn=_on_new_chat,
            inputs=[],
            outputs=[thread_id_state, chatbot, diagram_md, thread_radio],
        )

        thread_radio.select(
            fn=_on_select_thread,
            inputs=[thread_radio],
            outputs=[thread_id_state, chatbot, diagram_md],
        )

    return demo


def main() -> None:
    demo = create_app()
    demo.queue().launch(
        server_name=settings.GRADIO_HOST,
        server_port=settings.GRADIO_PORT,
        css=APP_CSS,
    )


if __name__ == "__main__":
    main()
