from dataclasses import asdict, fields

from langchain_core.documents import Document

from lang_rag_playground.core.logger import get_logger
from lang_rag_playground.models.citation_model import Citation
from lang_rag_playground.retrieval.vectordb_service import AsyncQdrantVectorDBService

logger = get_logger(__name__)

_CITATION_FIELDS = {field.name for field in fields(Citation)}


class RetrievalService:
    def __init__(
        self,
        vector_store: AsyncQdrantVectorDBService,
        collection_name: str,
    ):
        self.vector_store = vector_store
        self.collection_name = collection_name

    async def is_collection_exists(self, collection_name: str) -> bool:
        try:
            exists = await self.vector_store.is_collection_exists(collection_name)
            logger.info(
                f"Collection '{collection_name}' existence check: {exists}"
            )
            return exists
        except Exception as e:
            raise RuntimeError(
                f"Error occurred while checking collection existence: {e}"
            ) from e
    
    async def store_documents(self, documents: list[Document]) -> int:
        if not documents:
            raise ValueError("Documents list cannot be empty")
        if await self.vector_store.create_collection(self.collection_name):
            logger.info(f"Collection '{self.collection_name}' created.")
        to_store = [
            doc.model_copy(update={"metadata": self._to_citation_metadata(doc)})
            for doc in documents
        ]
        try:
            stored_count = await self.vector_store.store(
                collection_name=self.collection_name,
                documents=to_store,
            )
        except Exception as e:
            raise RuntimeError(f"Error occurred while storing documents: {e}") from e
        logger.info(
            f"Successfully stored {stored_count} documents in collection '{self.collection_name}'."
        )
        return stored_count

    async def search(self, query: str, top_k: int) -> list[Document]:
        if query is None or query.strip() == "":
            raise ValueError("Query cannot be empty")
        if top_k <= 0:
            raise ValueError("top_k must be a positive integer")
        try:
            chunks = await self.vector_store.search(
                query=query,
                collection_name=self.collection_name,
                top_k=top_k,
            )
        except Exception as e:
            raise RuntimeError(f"Error occurred while searching: {e}") from e
        logger.info(
            f"Successfully retrieved {len(chunks)} documents for query '{query}' from collection '{self.collection_name}'."
        )
        return [
            chunk.model_copy(
                update={"metadata": self._to_citation_metadata(chunk, strict=False)}
            )
            for chunk in chunks
        ]

    @staticmethod
    def _to_citation_metadata(doc: Document, strict: bool = True) -> dict:
        metadata = doc.metadata
        if strict:
            unknown = set(metadata) - _CITATION_FIELDS
            if unknown:
                raise ValueError(
                    f"Metadata has fields that are not part of Citation: {sorted(unknown)}"
                )
        else:
            metadata = {
                key: value for key, value in metadata.items() if key in _CITATION_FIELDS
            }
        citation = Citation(**metadata)
        citation.text = doc.page_content
        return asdict(citation)
