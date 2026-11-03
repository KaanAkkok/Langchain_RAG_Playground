class RAGError(Exception):
    """Base class for all errors raised by this package."""


class DocumentSavingError(RAGError):
    """Document saving failed."""


class DocumentExtractionError(RAGError):
    """Document extraction failed."""


class DocumentChunkingError(RAGError):
    """Document chunking failed."""


class RetrievalError(RAGError):
    """Document retrieval failed."""


class RerankerError(RAGError):
    """Reranking failed."""


class GraphStreamError(RAGError):
    """Graph streaming failed."""


class MemoryStoreError(RAGError):
    """Memory store operation failed."""


class MemoryRecallError(RAGError):
    """Memory recall failed."""


class LLMGenerationError(RAGError):
    """LLM generation failed."""


class InvalidGroundTruthSchemaError(RAGError):
    """Invalid ground truth data provided."""
