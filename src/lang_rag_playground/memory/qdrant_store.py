from __future__ import annotations

import asyncio
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from langgraph.store.base import (
    BaseStore,
    Op,
    PutOp,
    Result,
    SearchItem,
    SearchOp,
)
from qdrant_client import models

from lang_rag_playground.retrieval.vectordb_service import AsyncQdrantVectorDBService
from lang_rag_playground.core.settings import settings


class QdrantMemoryStore(BaseStore):
    def __init__(
        self,
        vector_db: AsyncQdrantVectorDBService,
        collection_name: str = settings.VECTORDB_MEMORY_COLLECTION_NAME,
    ) -> None:
        self.vector_db = vector_db
        self.collection_name = collection_name

    def ensure_collection(self) -> None:
        if self.vector_db.client.collection_exists(self.collection_name):
            return
        dimension = len(self.vector_db.embedding.embed_query("dimension probe"))
        self.vector_db.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=dimension,
                distance=models.Distance.COSINE,
            ),
        )

    @staticmethod
    def _validate_namespace(namespace: tuple[str, ...]) -> str:
        if len(namespace) != 2 or namespace[1] != "memories":
            raise ValueError(
                "QdrantMemoryStore only supports (user_id, 'memories') namespaces."
            )
        return namespace[0]

    def _point_id(self, namespace: tuple[str, ...], key: str) -> str:
        return str(uuid5(NAMESPACE_URL, f"{namespace!r}:{key}"))

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    def batch(self, ops: Iterable[Op]) -> list[Result]:
        raise RuntimeError("Use the asynchronous QdrantMemoryStore API.")

    async def abatch(self, ops: Iterable[Op]) -> list[Result]:
        results: list[Result] = []
        for op in ops:
            if isinstance(op, PutOp):
                await self._put(op)
                results.append(None)
            elif isinstance(op, SearchOp):
                results.append(await self._search(op))
            else:
                raise NotImplementedError(
                    "QdrantMemoryStore only supports memory put/search operations; "
                    f"received {type(op).__name__}."
                )
        return results

    async def _put(self, op: PutOp) -> None:
        user_id = self._validate_namespace(op.namespace)
        point_id = self._point_id(op.namespace, op.key)
        if op.value is None:
            await asyncio.to_thread(
                self.vector_db.client.delete,
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=[point_id]),
            )
            return

        now = self._now().isoformat()
        vector = await self.vector_db.embedding.aembed_query(
            str(op.value.get("content", ""))
        )
        payload = {
            "user_id": user_id,
            "key": op.key,
            "value": dict(op.value),
            "created_at": now,
            "updated_at": now,
        }
        await asyncio.to_thread(
            self.vector_db.client.upsert,
            collection_name=self.collection_name,
            points=[
                models.PointStruct(id=point_id, vector=vector, payload=payload)
            ],
        )

    async def _search(self, op: SearchOp) -> list[SearchItem]:
        user_id = self._validate_namespace(op.namespace_prefix)
        vector = await self.vector_db.embedding.aembed_query(op.query or "")
        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="user_id",
                    match=models.MatchValue(value=user_id),
                )
            ]
        )
        response = await asyncio.to_thread(
            self.vector_db.client.query_points,
            collection_name=self.collection_name,
            query=vector,
            query_filter=query_filter,
            limit=op.limit,
            offset=op.offset,
            with_payload=True,
        )
        return [
            self._search_item_from_payload(
                op.namespace_prefix, point.payload or {}, point.score
            )
            for point in response.points
        ]

    @staticmethod
    def _search_item_from_payload(
        namespace: tuple[str, ...],
        payload: dict[str, Any],
        score: float,
    ) -> SearchItem:
        return SearchItem(
            namespace=namespace,
            key=str(payload["key"]),
            value=dict(payload["value"]),
            created_at=datetime.fromisoformat(payload["created_at"]),
            updated_at=datetime.fromisoformat(payload["updated_at"]),
            score=score,
        )
