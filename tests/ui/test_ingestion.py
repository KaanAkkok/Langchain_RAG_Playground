from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.documents import Document

from lang_rag_playground.core.exceptions import DocumentExtractionError
from lang_rag_playground.ui import ingestion
from lang_rag_playground.ui.ingestion import ingest_files


@pytest.mark.asyncio
async def test_ingest_files_happy_path(tmp_path: Path):
    pdf = tmp_path / "tez.pdf"
    pdf.write_bytes(b"%PDF-1.4 dummy")

    extractor = MagicMock()
    extractor.extract.return_value = "Extracted markdown"
    chunker = MagicMock()
    chunker.chunk = AsyncMock(return_value=[Document(page_content="c1"), Document(page_content="c2")])
    retrieval = MagicMock()
    retrieval.store_documents = AsyncMock(return_value=2)

    steps = [msg async for msg in ingest_files([pdf], extractor, chunker, retrieval)]
    assert any("metin çıkarılıyor" in s for s in steps)
    assert any("2 chunk" in s for s in steps)
    assert any("Qdrant'a yazıldı" in s for s in steps)


@pytest.mark.asyncio
async def test_ingest_files_rejects_non_pdf_and_continues(tmp_path: Path):
    bad = tmp_path / "notlar.txt"
    bad.write_text("merhaba", encoding="utf-8")
    good = tmp_path / "ok.pdf"
    good.write_bytes(b"%PDF-1.4 ok")

    extractor = MagicMock()
    extractor.extract.return_value = "text"
    chunker = MagicMock()
    chunker.chunk = AsyncMock(return_value=[Document(page_content="c1")])
    retrieval = MagicMock()
    retrieval.store_documents = AsyncMock(return_value=1)

    steps = [msg async for msg in ingest_files([bad, good], extractor, chunker, retrieval)]
    assert any("❌" in s and "notlar.txt" in s for s in steps)
    assert any("ok.pdf" in s and "Qdrant'a yazıldı" in s for s in steps)


@pytest.mark.asyncio
async def test_ingest_files_handles_extraction_error_and_empty_chunks(tmp_path: Path):
    pdf1 = tmp_path / "bozuk.pdf"
    pdf1.write_bytes(b"%PDF-1.4")
    pdf2 = tmp_path / "bos.pdf"
    pdf2.write_bytes(b"%PDF-1.4")

    extractor = MagicMock()
    extractor.extract.side_effect = [DocumentExtractionError("OCR hatası"), "metin"]
    chunker = MagicMock()
    chunker.chunk = AsyncMock(return_value=[])
    retrieval = MagicMock()
    retrieval.store_documents = AsyncMock()

    steps = [msg async for msg in ingest_files([pdf1, pdf2], extractor, chunker, retrieval)]
    assert any("❌" in s and "bozuk.pdf" in s for s in steps)
    assert any("❌" in s and "bos.pdf" in s for s in steps)


@pytest.mark.asyncio
async def test_ingest_files_handles_missing_and_oversized_files(tmp_path: Path, monkeypatch):
    missing = tmp_path / "yok.pdf"
    huge = tmp_path / "dev.pdf"
    huge.write_bytes(b"%PDF-1.4 oversized")
    monkeypatch.setattr(ingestion, "MAX_FILE_SIZE_BYTES", 5)

    extractor = MagicMock()
    chunker = MagicMock()
    retrieval = MagicMock()

    steps = [msg async for msg in ingest_files([missing, huge], extractor, chunker, retrieval)]
    assert any("❌" in s and "yok.pdf" in s and "Dosya bulunamadı" in s for s in steps)
    assert any("❌" in s and "dev.pdf" in s and "50 MB" in s for s in steps)
