import re
import unicodedata
from hashlib import sha256
from pathlib import Path
from typing import Literal

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from lang_rag_playground.core.logger import get_logger
from lang_rag_playground.core.settings import settings
from lang_rag_playground.ingestion.document_extractor import (
    PAGE_BREAK_PLACEHOLDER,
)
from lang_rag_playground.models.citation_model import Citation

logger = get_logger(__name__)


INVISIBLE_RE = re.compile(r"[\u200b\u200c\u200d\ufeff]")
SENTENCE_SPLIT_RE = [
    r"(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ])",  # Sentence boundaries
    r"(?<=[.!?])\s+(?=[\"'“”‘’])",  # Sentence boundaries with quotes
    r"(?<=[.!?])\s+(?=[\d])",  # Sentence boundaries with numbers
    r"(?<=[.!?])\s+(?=[\(\[\{])",  # Sentence boundaries with opening brackets
    r"(?<=[.!?])\s+(?=[\)\]\}])",  # Sentence boundaries with closing brackets
    r"(?<=[.!?])\s+(?=[,;:])",  # Sentence boundaries with punctuation
    r"(?<=[.!?])\s+(?=[-–—])",  # Sentence boundaries with dashes
    r"(?<=[.!?])\s+(?=[/\\|])",  # Sentence boundaries with slashes
    r"(?<=[.!?])\s+(?=[@#$%^&*+=<>~`])",  # Sentence boundaries with special characters
    r"(?<=[.!?])\s+(?=[_])",  # Sentence boundaries with underscores
    r"(?<=[.!?])\s+(?=[…])",  # Sentence boundaries with ellipsis
]
IMAGE_TAG_RE = re.compile(r"<!-- image -->")
HYPHEN_BREAK_RE = re.compile(r"(?<=\w)-\n(?=[a-zçğıöşü])")
HEADERS = [(f"{'#' * i}", f"h{i}") for i in range(1, 7)]


def clean_markdown(md: str) -> str:
    text = unicodedata.normalize("NFC", md).replace("\r", "")
    text = INVISIBLE_RE.sub("", text)
    text = HYPHEN_BREAK_RE.sub("", text)
    text = IMAGE_TAG_RE.sub("", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class DocumentChunker:
    def __init__(
        self,
        embedding_model: Embeddings,
        header_splitter_strip_headers: bool = True,
        semantic_chunker_threshold_type: Literal[
            "percentile", "standard_deviation", "interquartile", "gradient"
        ] = "percentile",
        semantic_chunker_breakpoint_threshold_amount: float = settings.BREAK_PERCENTILE,
        max_chunk_chars: int = settings.MAX_CHUNK_CHARS,
        min_chunk_chars: int = settings.MIN_CHUNK_CHARS,
        overlap_chars: int = settings.OVERLAP_CHARS,
        buffer_size: int = settings.SEMANTIC_CHUNKER_BUFFER_SIZE,
    ):
        self.embedding_model = embedding_model
        self.max_chunk_chars = max_chunk_chars
        self._validate_config()
        # TODO (Görev 1): Öğrenci Rehberi > Görev 1
        # Adım 1: self.header_splitter = MarkdownHeaderTextSplitter(HEADERS, strip_headers=...)
        # Adım 2: self.semantic_splitter = SemanticChunker(embedding_model, eşik tipi/miktarı, min_chunk_size, buffer_size)
        # Adım 3: self.size_splitter = RecursiveCharacterTextSplitter(chunk_size, chunk_overlap, SENTENCE_SPLIT_RE regex ayraçları)
        # --- ÇÖZÜM BAŞLANGIÇ ---
        self.header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=HEADERS,
            strip_headers=header_splitter_strip_headers,
        )
        self.semantic_splitter = SemanticChunker(
            embeddings=embedding_model,
            breakpoint_threshold_type=semantic_chunker_threshold_type,
            breakpoint_threshold_amount=semantic_chunker_breakpoint_threshold_amount,
            min_chunk_size=min_chunk_chars,
            buffer_size=buffer_size,
        )
        self.size_splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chunk_chars,
            chunk_overlap=overlap_chars,
            is_separator_regex=True,
            separators=SENTENCE_SPLIT_RE,
            length_function=len,
        )
        # --- ÇÖZÜM BİTİŞ ---

    def _validate_config(self) -> None:
        if self.embedding_model is None:
            raise ValueError("Embedding model must be provided for semantic chunking.")
        if not isinstance(self.embedding_model, Embeddings):
            raise TypeError("embedding_model must implement LangChain Embeddings.")

    @staticmethod
    def _breadcrumb(metadata: dict) -> str:
        return " > ".join(metadata[k] for k in sorted(metadata) if k.startswith("h"))

    async def chunk(self, content: str, document_path: Path | str) -> list[Document]:
        path = Path(document_path)
        chunks: list[Document] = []

        for page_no, page in enumerate(content.split(PAGE_BREAK_PLACEHOLDER), start=1):
            cleaned_page = clean_markdown(page)
            if not cleaned_page:
                continue

            # 1. Markdown başlıklarına göre böl + metadata ekle
            sections: list[Document] = []
            for section in self.header_splitter.split_text(cleaned_page):
                text = section.page_content.strip()
                if not text:
                    continue
                section_title = self._breadcrumb(section.metadata)
                section = Document(
                    page_content=section.page_content.strip(),
                    metadata=Citation(
                        page=page_no,
                        document_name=path.name,
                        document_path=str(path),
                        section_title=section_title,
                        text=text,
                    ).__dict__,
                )
                sections.append(section)

            # 2. Semantic chunking
            page_docs = await self.semantic_splitter.atransform_documents(sections)

            # 3. Max boyutu aşanları böl (küçük olanlara dokunmaz)
            chunks.extend(self.size_splitter.split_documents(page_docs))

        # 4. ID'leri en sonda, tüm dokümanda benzersiz ver
        for i, chunk in enumerate(chunks, start=1):
            citation = Citation(**chunk.metadata)
            citation.chunk_id = sha256(
                f"{path.stem}|{i}|{chunk.page_content}".encode()
            ).hexdigest()
            citation.paragraph_no = i
            citation.text = chunk.page_content
            chunk.metadata = citation.__dict__
            logger.info(f"Chunk {i} created: {citation.chunk_id}")
        return chunks
