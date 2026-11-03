import re
import unicodedata
from collections.abc import AsyncIterator
from typing import Any, Literal, cast

import gradio as gr

from lang_rag_playground.core.settings import settings
from lang_rag_playground.ui.APP_CSS import APP_CSS
from lang_rag_playground.ui.APP_JS import APP_JS
from lang_rag_playground.ui.chat import respond
from lang_rag_playground.ui.evaluation import (
    EVAL_TABLE_HEADERS,
    graph_label,
    run_evaluation,
)
from lang_rag_playground.ui.graph_view import render
from lang_rag_playground.ui.history import list_threads, load_thread, new_thread_id
from lang_rag_playground.ui.ingestion import ingest_files
from lang_rag_playground.ui.services import AppServices, build_app_services


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
    services_holder: list[AppServices | None] = [services]

    def get_services() -> AppServices:
        current_services = services_holder[0]
        if current_services is None:
            raise gr.Error("Başlamak için graph türünü seçip Başla'ya basın.")
        return current_services

    with gr.Blocks(
        title="Agentic RAG Playground", fill_height=True, css=APP_CSS, js=APP_JS
    ) as demo:
        user_id_state = gr.State("")
        thread_id_state = gr.State(new_thread_id)

        with gr.Column(visible=True, elem_id="welcome-screen") as welcome_screen:
            gr.Markdown(
                "# Agentic RAG Playground\n\n"
                "Başlamak için isminizi yazın.",
                elem_id="welcome-title",
            )
            name_input = gr.Textbox(
                label="İsminiz",
                placeholder="Memory kaydı için gerekiyor.",
                max_lines=1,
                autofocus=True,
            )
            graph_type = gr.Radio(
                label="Grafiğin Türü",
                choices=["agentic", "workflow"],
                value="agentic",
                interactive=True,
            )
            start_button = gr.Button("Başla", variant="primary")

        with gr.Column(visible=False) as workspace:
            with gr.Sidebar(open=False):
                new_chat_btn = gr.Button("+ Yeni Sohbet", variant="primary")
                gr.Markdown("**Geçmiş Sohbetler**")
                thread_radio = gr.Radio(
                    label="Geçmiş Sohbetler",
                    choices=[],
                    interactive=True,
                    container=False,
                    elem_id="thread-list",
                )

            with gr.Row(scale=1, equal_height=True):
                with gr.Column(scale=1):
                    diagram_md = gr.HTML(
                        value=(
                            render(services.mermaid_diagram)
                            if services is not None
                            else "<p>Grafik türünü seçip Başla'ya basın.</p>"
                        ),
                        elem_id="graph-diagram",
                        max_height=850,
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
            with gr.Sidebar(position="right", open=False, width=380):
                eval_graph_label = gr.Markdown(
                    f"### Evaluation\nTest edilen graph: `{graph_label(services)}`"
                    if services is not None
                    else "### Evaluation"
                )
                eval_button = gr.Button("Eval çalıştır", variant="secondary")
                eval_status = gr.Markdown()
                eval_table = gr.Dataframe(
                    headers=EVAL_TABLE_HEADERS,
                    datatype=["str", "str", "number"],
                    interactive=False,
                    wrap=True,
                )

        def start_session(
            name: str, selected_graph_type: str
        ) -> tuple[
            dict[str, Any],
            dict[str, Any],
            str,
            str,
            str,
        ]:
            normalized_name = unicodedata.normalize("NFKC", name).strip()
            if not normalized_name:
                raise gr.Error("Lütfen isminizi yazın.")
            user_key = re.sub(r"[^\w-]+", "_", normalized_name, flags=re.UNICODE)
            user_key = user_key.strip("_-")
            if not user_key:
                raise gr.Error("Geçerli bir isim yazın.")
            services_holder[0] = build_app_services(
                cast(Literal["agentic", "workflow"], selected_graph_type)
            )
            current_services = get_services()
            return (
                gr.update(visible=False),
                gr.update(visible=True),
                f"user_{user_key.casefold()}",
                render(current_services.mermaid_diagram),
                f"### Evaluation\nTest edilen graph: `{graph_label(current_services)}`",
            )

        async def _on_submit(
            user_input: dict[str, Any] | None,
            chat_history: list[Any],
            user_id: str,
            thread_id: str,
        ) -> AsyncIterator[tuple[list[Any], str, dict[str, Any], dict[str, Any]]]:
            current_services = get_services()
            async for out in handle_submit(
                user_input, chat_history, user_id, thread_id, current_services
            ):
                yield out

        def _on_new_chat() -> tuple[str, list[Any], str, dict[str, Any]]:
            current_services = get_services()
            return (
                new_thread_id(),
                [],
                render(current_services.mermaid_diagram),
                gr.update(value=None),
            )

        async def _on_select_thread(
            selected_thread_id: str | None,
        ) -> tuple[Any, Any, Any]:
            if not selected_thread_id:
                return gr.update(), gr.update(), gr.update()
            current_services = get_services()
            messages = await load_thread(current_services.graph, selected_thread_id)
            return (
                selected_thread_id,
                messages,
                render(current_services.mermaid_diagram),
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

        async def _on_eval() -> AsyncIterator[tuple[str, Any, dict[str, Any]]]:
            async for out in run_evaluation(get_services()):
                yield out

        # concurrency_limit=1: every run deletes and restores the evaluation collection
        eval_button.click(
            fn=_on_eval,
            inputs=[],
            outputs=[eval_status, eval_table, eval_button],
            concurrency_limit=1,
        )

        start_button.click(
            fn=start_session,
            inputs=[name_input, graph_type],
            outputs=[
                welcome_screen,
                workspace,
                user_id_state,
                diagram_md,
                eval_graph_label,
            ],
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
