import asyncio
import json
import uuid
from pathlib import Path

import httpx
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_qdrant import (
    FastEmbedSparse,
    QdrantVectorStore,
    RetrievalMode,
)
from qdrant_client import QdrantClient, models

from lang_rag_playground.core.settings import settings


class AsyncQdrantVectorDBService:

    def __init__(
        self,
        embedding: Embeddings,
        host: str = settings.QDRANT_HOST,
        port: int = settings.QDRANT_PORT,
        prefer_grpc: bool = False,
        url: str | None = None,
        api_key: str | None = None,
    ):
        if embedding is None:
            raise ValueError("Embedding model is required")
        self.embedding = embedding
        self.url = url or f"http://{host}:{port}"
        self.api_key = api_key
        self.client = QdrantClient(
            url=self.url,
            api_key=api_key,
            prefer_grpc=prefer_grpc,
        )
        self.sparse_embedding = FastEmbedSparse(model_name="Qdrant/bm25")

    def get_vector_store(self, collection_name: str) -> QdrantVectorStore:
        """Koleksiyon icin hibrit (dense + sparse) bir QdrantVectorStore dondurur.

        Girdi: collection_name (str).
        Cikti: QdrantVectorStore.
        Adimlar: client/embedding/sparse_embedding'i ver, HYBRID modunu sec,
        vektor adlarini "dense" ve "sparse" yap.
        """
        # TODO (Görev 2): Öğrenci Rehberi > Görev 2
        # Adım 1: QdrantVectorStore(...) oluştur (client, collection_name, embedding, sparse_embedding)
        # Adım 2: retrieval_mode=RetrievalMode.HYBRID
        # Adım 3: vector_name="dense", sparse_vector_name="sparse"
        raise NotImplementedError("TODO (Görev 2): Öğrenci Rehberi > Görev 2")

    @staticmethod
    def _point_id(doc: Document) -> str:
        if doc.id:
            key = doc.id
        else:
            key = doc.page_content + json.dumps(
                doc.metadata, sort_keys=True, default=str
            )
        return str(uuid.uuid5(uuid.NAMESPACE_URL, key))

    async def is_collection_exists(self, collection_name: str) -> bool:
        try:
            exists = await asyncio.to_thread(
                self.client.collection_exists, collection_name
            )
            return exists
        except Exception as e:
            raise RuntimeError(
                f"Error occurred while checking collection existence: {e}"
            ) from e

    async def create_collection(self, collection_name: str) -> bool:
        """Koleksiyon yoksa dense + sparse yapilandirmasiyla olusturur.

        Girdi: collection_name (str).
        Cikti: Koleksiyon varsa False; yeni olusturulduysa client.create_collection sonucu.
        Adimlar:
          1. Embedding ile boyutu olc: len(await self.embedding.aembed_query("dimension probe"))
          2. "dense": VectorParams(size=boyut, distance=COSINE)
          3. "sparse": SparseVectorParams(index=SparseIndexParams(on_disk=False))
          4. Bloklayan client cagrisini asyncio.to_thread ile calistir.
        """
        exist = await self.is_collection_exists(collection_name)
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
        """Dokumanlari deterministik id'lerle Qdrant'a yazar.

        Girdi: collection_name, documents.
        Cikti: Yazilan dokuman sayisi (int).
        Adimlar:
          1. vector_store = self.get_vector_store(collection_name)
          2. Her dokuman icin self._point_id(doc) ile id listesi uret
          3. await vector_store.aadd_documents(documents, ids=point_ids)
          4. Hata olursa RuntimeError("Failed to store documents in Qdrant: ...") firlat
          5. Dönen id sayisi dokuman sayisina esit degilse veya 0 ise RuntimeError firlat
          6. len(ids) dondur
        """
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
        """Hibrit arama yapar ve her dokumanin metadata'sina "score" ekler.

        Girdi: query, collection_name, top_k.
        Cikti: Skorlu Document listesi (koleksiyon yoksa bos liste).
        Adimlar:
          1. Koleksiyon yoksa [] dondur (client.collection_exists, asyncio.to_thread ile)
          2. vector_store.asimilarity_search_with_score(query=query, k=top_k)
          3. Hata olursa RuntimeError("Failed to search in Qdrant: ...") firlat
          4. doc.model_copy(update={"metadata": {**doc.metadata, "score": score}})
        """
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

    async def restore_snapshot(self, collection_name: str, location: Path | str) -> bool:
        if not collection_name or not collection_name.strip():
            raise ValueError("Collection name must be provided")
        if not location:
            raise ValueError("Snapshot location must be provided")
        if isinstance(location, str):
            location = Path(location)
        if not location.is_file():
            raise FileNotFoundError(f"Snapshot file does not exist: {location}")
        headers = {"api-key": self.api_key} if self.api_key else {}
        try:
            async with httpx.AsyncClient(timeout=300) as http_client:
                with location.open("rb") as snapshot_file:
                    response = await http_client.post(
                        f"{self.url}/collections/{collection_name}/snapshots/upload",
                        params={"priority": "snapshot", "wait": "true"},
                        headers=headers,
                        files={"snapshot": (location.name, snapshot_file)},
                    )
            response.raise_for_status()
            return True
        except Exception as e:
            raise RuntimeError(
                f"Failed to restore snapshot '{location.name}' for collection '{collection_name}': {e}"
            ) from e

    async def delete_collection(self, collection_name: str) -> bool:
        if not collection_name or not collection_name.strip():
            raise ValueError("Collection name must be provided")
        try:
            await asyncio.to_thread(self.client.delete_collection, collection_name)
            return True
        except Exception as e:
            raise RuntimeError(
                f"Failed to delete collection '{collection_name}': {e}"
            ) from e