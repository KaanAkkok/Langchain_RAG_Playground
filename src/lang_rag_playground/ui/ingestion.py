import asyncio
from collections.abc import AsyncIterator, Sequence
from pathlib import Path

from lang_rag_playground.core.exceptions import (
    DocumentChunkingError,
    DocumentExtractionError,
)
from lang_rag_playground.core.settings import settings
from lang_rag_playground.ingestion.document_chunker import DocumentChunker
from lang_rag_playground.ingestion.document_extractor import DocumentExtractor
from lang_rag_playground.retrieval.retrieval_service import RetrievalService

MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024


async def ingest_files(
    paths: Sequence[str | Path],
    extractor: DocumentExtractor,
    chunker: DocumentChunker,
    retrieval_service: RetrievalService,
) -> AsyncIterator[str]:
    supported_extensions = [ext.lower() for ext in settings.SUPPORTED_FILE_TYPES]

    for raw_path in paths:
        file_path = Path(raw_path)
        name = file_path.name

        if not file_path.is_file():
            yield f"[INGESTION] {name}: Dosya bulunamadı."
            continue

        if file_path.suffix.lower() not in supported_extensions:
            yield (
                f"[INGESTION] {name}: Desteklenmeyen dosya türü ({file_path.suffix}). "
                "Yalnızca PDF dosyaları kabul edilir."
            )
            continue

        if file_path.stat().st_size > MAX_FILE_SIZE_BYTES:
            yield f"[INGESTION] {name}: Dosya boyutu 50 MB sınırını aşıyor."
            continue

        try:
            yield f"[INGESTION - EXTRACTION] {name}: metin çıkarılıyor..."
            content = await asyncio.to_thread(extractor.extract, file_path)
            chunks = await chunker.chunk(content, file_path)
            if not chunks:
                yield f"❌ {name}: Belgeden metin parçası (chunk) üretilemedi."
                continue
            yield f"[INGESTION - CHUNKING] {name}: {len(chunks)} chunk oluşturuldu, Qdrant'a yazılıyor..."
            await retrieval_service.store_documents(chunks)
            yield f"[INGESTION - EMBEDDING] {name}: {len(chunks)} chunk --> Qdrant'a yazıldı"
        except (DocumentExtractionError, DocumentChunkingError, Exception) as exc:
            yield f"❌ {name}: {exc}"
            continue
