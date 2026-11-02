class RAGError(Exception):
    """Base class for all errors raised by this package."""


class DocumentSavingError(RAGError):
    """Document saving failed."""


class DocumentExtractionError(RAGError):
    """Document extraction failed."""


class DocumentChunkingError(RAGError):
    """Document chunking failed."""
