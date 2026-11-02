import asyncio
import json
import uuid

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_qdrant import (
    FastEmbedSparse,
    QdrantVectorStore,
    RetrievalMode,
)
from qdrant_client import QdrantClient, models


class AsyncQdrantVectorDBService:

    def __init__(
        self,
        embedding: Embeddings,
        host: str,
        port: int,
        prefer_grpc: bool = False,
        url: str | None = None,
        api_key: str | None = None,
    ):
        if embedding is None:
            raise ValueError("Embedding model is required")
        self.embedding = embedding
        self.url = url or f"http://{host}:{port}"
        self.client = QdrantClient(
            url=self.url,
            api_key=api_key,
            prefer_grpc=prefer_grpc,
        )
        self.sparse_embedding = FastEmbedSparse(model_name="Qdrant/bm25")

    def get_vector_store(self, collection_name: str) -> QdrantVectorStore:
        return QdrantVectorStore(
            client=self.client,
            collection_name=collection_name,
            embedding=self.embedding,
            sparse_embedding=self.sparse_embedding,
            retrieval_mode=RetrievalMode.HYBRID,
            vector_name="dense",
            sparse_vector_name="sparse",
        )

    @staticmethod
    def _point_id(doc: Document) -> str:
        if doc.id:
            key = doc.id
        else:
            key = doc.page_content + json.dumps(
                doc.metadata, sort_keys=True, default=str
            )
        return str(uuid.uuid5(uuid.NAMESPACE_URL, key))

    async def create_collection(self, collection_name: str) -> bool:
        exist = await asyncio.to_thread(self.client.collection_exists, collection_name)
        if exist:
            return False
        sample_vector_size = len(await self.embedding.aembed_query("dimension probe"))
        result = await asyncio.to_thread(
            self.client.create_collection,
            collection_name=collection_name,
            vectors_config={
                "dense": models.VectorParams(
                    size=sample_vector_size,
                    distance=models.Distance.COSINE,
                )
            },
            sparse_vectors_config={
                "sparse": models.SparseVectorParams(
                    index=models.SparseIndexParams(on_disk=False)
                )
            },
        )
        return result

    async def store(
        self,
        collection_name: str,
        documents: list[Document],
    ) -> int:
        vector_store = self.get_vector_store(collection_name)
        point_ids = [self._point_id(doc) for doc in documents]
        try:
            ids = await vector_store.aadd_documents(documents, ids=point_ids)
        except Exception as e:
            raise RuntimeError(f"Failed to store documents in Qdrant: {e}") from e
        if len(ids) != len(documents):
            raise RuntimeError(
                f"Expected to store {len(documents)} documents, but only stored {len(ids)}."
            )
        if len(ids) == 0:
            raise RuntimeError("No documents were stored in Qdrant.")
        return len(ids)

    async def search(
        self,
        query: str,
        collection_name: str,
        top_k: int,
    ) -> list[Document]:
        if query is None or query.strip() == "":
            raise ValueError("Query cannot be empty")
        if collection_name is None or collection_name.strip() == "":
            raise ValueError("Collection name must be provided")
        if top_k <= 0:
            raise ValueError("top_k must be a positive integer")
        if not await asyncio.to_thread(self.client.collection_exists, collection_name):
            return []
        vector_store = self.get_vector_store(collection_name)
        try:
            chunks_with_scores = await vector_store.asimilarity_search_with_score(
                query=query,
                k=top_k,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to search in Qdrant: {e}") from e
        return [
            doc.model_copy(update={"metadata": {**doc.metadata, "score": score}})
            for doc, score in chunks_with_scores
        ]
