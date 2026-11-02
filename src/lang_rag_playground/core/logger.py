import logging
import sys

from lang_rag_playground.core.settings import settings

_APP_LOGGER_NAME = "rag"
_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _configure_app_logger() -> logging.Logger:
    app_logger = logging.getLogger(_APP_LOGGER_NAME)
    if not app_logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
        app_logger.addHandler(handler)
    app_logger.setLevel(settings.LOG_LEVEL.upper())
    app_logger.propagate = False

    for logger_name in (
        "httpx",
        "httpx2",
        "httpcore",
        "docling",
        "docling_core",
        "docling_ibm_models",
        "docling_parse",
        "rapidocr",
        "easyocr",
        "pdfminer",
    ):
        logging.getLogger(logger_name).setLevel(logging.ERROR)

    return app_logger


def get_logger(name: str) -> logging.Logger:
    _configure_app_logger()
    return logging.getLogger(
        f"{_APP_LOGGER_NAME}.{name.removeprefix('rag_playground.')}"
    )
