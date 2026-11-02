from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, override

from docling.datamodel.pipeline_options import (
    OcrMode,
    OcrOptions,
    TesseractCliOcrOptions,
)


class OCRlang(Enum):
    ENGLISH = "eng"
    TURKISH = "tur"


class OCRFactory(ABC):
    def __init__(
        self,
        lang: list[OCRlang],
        force_full_page_ocr: bool = False,
    ):
        self.lang = lang
        self.force_full_page_ocr = force_full_page_ocr

    @abstractmethod
    def create_options(self, **kwargs: Any) -> OcrOptions:
        pass


class TesseractOCRFactory(OCRFactory):
    @override
    def create_options(self, psm: int = 6, **kwargs: Any) -> TesseractCliOcrOptions:

        ocr_mode = OcrMode.DEFAULT
        if self.force_full_page_ocr:
            ocr_mode = OcrMode.FULL_PAGE
        return TesseractCliOcrOptions(
            lang=[lang.value for lang in self.lang],
            mode=ocr_mode,
            psm=psm,
        )


def get_ocr_config(
    factory: OCRFactory, extra_settings: dict[str, Any] | None = None
) -> OcrOptions:
    settings = extra_settings or {}
    return factory.create_options(**settings)


def get_default_ocr_options() -> TesseractCliOcrOptions:
    default_factory = TesseractOCRFactory(
        lang=[OCRlang.ENGLISH, OCRlang.TURKISH], force_full_page_ocr=False
    )
    return default_factory.create_options()
