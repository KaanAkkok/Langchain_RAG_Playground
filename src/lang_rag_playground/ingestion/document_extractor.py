import logging
import re
import unicodedata
from pathlib import Path

import pdfplumber
from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.datamodel.backend_options import (
    DEFAULT_MAX_IMAGE_PIXELS,
    PdfBackendOptions,
)
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    LayoutOptions,
    OcrOptions,
    PdfPipelineOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from pdfplumber.utils.exceptions import MalformedPDFException, PdfminerException

from lang_rag_playground.core.exceptions import DocumentExtractionError
from lang_rag_playground.core.logger import get_logger
from lang_rag_playground.core.settings import settings
from lang_rag_playground.ingestion.ocr_factory import (
    OCRFactory,
    get_default_ocr_options,
    get_ocr_config,
)

for _docling_logger in (
    "docling",
    "docling_core",
    "docling_ibm_models",
    "docling_parse",
):
    logging.getLogger(_docling_logger).setLevel(logging.ERROR)
logger = get_logger(__name__)


ACCENTS = {
    "\u00a8": "\u0308",  # ¨  -> ö, ü
    "\u00b8": "\u0327",  # ¸  -> ç, ş
    "\u02d8": "\u0306",  # ˘  -> ğ
    "\u02d9": "\u0307",  # ˙  -> İ
    "\u00b4": "\u0301",  # ´  -> á, é
    "\u0060": "\u0300",  # `  -> à, è
    "\u02c6": "\u0302",  # ˆ  -> â, î
    "\u02dc": "\u0303",  # ˜  -> ñ, ã
    "\u02c7": "\u030c",  # ˇ  -> č, š
}
PAGE_BREAK_PLACEHOLDER = "\n\n---[PAGE BREAK]---\n\n"
letters = r"[^\W\d_]"
accent_class = "".join(ACCENTS)
before = re.compile(rf"([{accent_class}])\s?({letters})")
after = re.compile(rf"({letters})\s?([{accent_class}])")


def fix_accents(text: str) -> str:
    text = before.sub(lambda m: m.group(2) + ACCENTS[m.group(1)], text)
    text = after.sub(lambda m: m.group(1) + ACCENTS[m.group(2)], text)
    return unicodedata.normalize("NFKC", text)


class DocumentExtractor:
    def __init__(
        self,
        ocr_enabled: bool = False,
        force_backend_text: bool = False,
        image_scale: float = 3.0,
        ocr_factory: OCRFactory | None = None,
        layout_enabled: bool = False,
        table_enabled: bool = False,
        do_cell_matching: bool = False,
    ):
        self.ocr_enabled = ocr_enabled
        self.force_backend_text = force_backend_text
        self.image_scale = image_scale
        self.ocr_factory = ocr_factory
        self.layout_enabled = layout_enabled
        self.table_enabled = table_enabled
        self.do_cell_matching = do_cell_matching
        self.ocr_options: OcrOptions | None = None

    def _build_pdf_pipeline(self, do_ocr: bool | None = None) -> PdfPipelineOptions:
        if self.ocr_options is None:
            if self.ocr_factory is None:
                self.ocr_options = get_default_ocr_options()
            else:
                self.ocr_options = get_ocr_config(self.ocr_factory)
        pipeline_options = PdfPipelineOptions(
            do_ocr=self.ocr_enabled if do_ocr is None else do_ocr,
            do_table_structure=False,
            force_backend_text=self.force_backend_text,
            ocr_options=self.ocr_options,
            generate_picture_images=False,
            images_scale=self.image_scale,
        )
        if self.layout_enabled:
            from docling.datamodel.layout_model_specs import DOCLING_LAYOUT_HERON

            pipeline_options.layout_options = LayoutOptions(
                model_spec=DOCLING_LAYOUT_HERON
            )
        if self.table_enabled:
            from docling.datamodel.pipeline_options import (
                TableFormerMode,
                TableStructureOptions,
            )

            pipeline_options.do_table_structure = True
            pipeline_options.table_structure_options = TableStructureOptions(
                mode=TableFormerMode.ACCURATE, do_cell_matching=self.do_cell_matching
            )
        return pipeline_options

    def _get_converter(self, do_ocr: bool | None = None) -> DocumentConverter:
        pipeline_options = self._build_pdf_pipeline(do_ocr=do_ocr)
        converter = DocumentConverter(
            allowed_formats=[InputFormat.PDF],
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options,
                    backend=DoclingParseDocumentBackend,
                    backend_options=PdfBackendOptions(
                        enable_remote_fetch=False,
                        enable_local_fetch=True,
                        kind="pdf",
                        enforce_same_font=False,
                        include_bitmap_images=False,
                        max_image_pixels=DEFAULT_MAX_IMAGE_PIXELS,
                    ),
                )
            },
        )
        return converter

    def _is_digital(self, file_path: Path) -> bool:
        try:
            with pdfplumber.open(file_path) as pdf:
                total = len(pdf.pages)
                start = 1 if total > 1 else 0
                sample = pdf.pages[start : start + 4]
                scores = [len((p.extract_text() or "").strip()) for p in sample]
                if not scores:
                    return False
                digital_pages = sum(1 for s in scores if s > 80)
                return digital_pages >= len(scores) / 2
        except (OSError, PdfminerException, MalformedPDFException) as e:
            logger.warning(
                f"Could not inspect PDF text layer for {file_path}, treating as scanned: {e}"
            )
            return False

    def extract(self, file_path: Path) -> str:
        if not file_path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")
        if file_path.suffix.lower() not in settings.SUPPORTED_FILE_TYPES:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")
        is_digital = self._is_digital(file_path)
        if is_digital:
            logger.info(f"Processing digital PDF {file_path}")
            converter = self._get_converter(do_ocr=False)
        else:
            logger.info(
                f"Processing scanned PDF {file_path} (OCR enabled: {self.ocr_enabled})"
            )
            converter = self._get_converter()
        logger.info(
            f"Extracting text from {file_path} (OCR enabled: {self.ocr_enabled})"
        )
        try:
            result = converter.convert(file_path)
        except DocumentExtractionError as e:
            logger.exception(f"Failed to convert {file_path}")
            raise RuntimeError(f"Failed to convert {file_path}: {e!s}") from e
        document = fix_accents(
            result.document.export_to_markdown(
                page_break_placeholder=PAGE_BREAK_PLACEHOLDER
            )
        )
        if not document or not document.strip():
            raise ValueError(
                "The PDF does not appear to contain extractable text. "
                "Enable OCR to process scanned pages."
            )
        return document
