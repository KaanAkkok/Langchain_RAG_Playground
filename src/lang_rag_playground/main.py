

from lang_rag_playground.core.settings import settings
from lang_rag_playground.ui.APP_CSS import APP_CSS
from lang_rag_playground.ui.app import create_app


def main() -> None:
    demo = create_app()
    demo.queue().launch(
        server_name=settings.GRADIO_HOST,
        server_port=settings.GRADIO_PORT,
        css=APP_CSS,
    )


if __name__ == "__main__":
    main()