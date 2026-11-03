import asyncio
import math
from pathlib import Path
from typing import Literal

from langchain_core.runnables import Runnable

from lang_rag_playground.core.exceptions import RetrievalError
from lang_rag_playground.core.logger import get_logger
from lang_rag_playground.core.settings import settings
from lang_rag_playground.evaluation.evaluation_service import EvaluationService
from lang_rag_playground.retrieval.reranking import rerank_documents, build_reranker_chain
from lang_rag_playground.retrieval.retrieval_service import RetrievalService

logger = get_logger(__name__)


RETRIEVAL_EVAL_RESULTS_SCHEMA: dict[str, dict[str, float]] = {
    "Retrieval Effectiveness Metrics": {
        "precision": 0.0,
        "recall": 0.0,
        "hit_rate": 0.0,
        "f1": 0.0,
    },
    "Ranking Quality Metrics": {"mrr": 0.0, "ndcg": 0.0},
}


class RetrievalEvaluator(EvaluationService):
    def __init__(
        self,
        retriever: RetrievalService,
        reranker_chain: Runnable,
        chunk_id_tag: str = settings.GROUNDTRUTH_CHUNK_ID_TAG,
        document_id_tag: str = settings.GROUNDTRUTH_DOCUMENT_ID_TAG,
        collection_name: str = settings.VECTORDB_EVALUATION_COLLECTION_NAME,
        eval_level: Literal[1, 2] = settings.RETRIEVAL_EVALUATION_LEVEL,
        ground_truth_path: Path | str = settings.GROUND_TRUTH_PATH,
    ):
        self.retriever = retriever
        self.reranker_chain = reranker_chain
        self.collection_name = collection_name
        super().__init__(ground_truth_path)
        self.eval_level = eval_level
        self.chunk_id_tag = chunk_id_tag
        self.document_id_tag = document_id_tag
        self._validate_config()

    def _validate_config(self):
        if not self.retriever or not isinstance(self.retriever, RetrievalService):
            raise ValueError(
                "Retriever service must be provided and be an instance of RetrievalService."
            )
        if not self.collection_name or not isinstance(self.collection_name, str):
            raise ValueError("Collection name must be a non-empty string.")
        if not isinstance(self.eval_level, int) or self.eval_level not in (1, 2):
            raise ValueError(
                "Evaluation level must be either 1 (passage-level) or 2 (document-level)."
            )
        if not self.chunk_id_tag or not isinstance(self.chunk_id_tag, str):
            raise ValueError("Chunk ID tag must be a non-empty string.")
        if not self.document_id_tag or not isinstance(self.document_id_tag, str):
            raise ValueError("Document ID tag must be a non-empty string.")

    def _get_chunk_ids_and_docs(
        self, chunks: list[dict]
    ) -> tuple[list[str], list[str]]:
        if not chunks or not self.chunk_id_tag or not self.document_id_tag:
            return [], []
        if not isinstance(chunks, list):
            raise TypeError(f"Chunks must be a list, got {type(chunks)}")
        relevant_chunk_ids = []
        relevant_doc_ids = []
        for chunk in chunks:
            if not isinstance(chunk, dict):
                raise TypeError(f"Each chunk must be a dict, got {type(chunk)}")
            chunk_id = chunk.get(self.chunk_id_tag)
            document_id = chunk.get(self.document_id_tag)
            if chunk_id is not None:
                relevant_chunk_ids.append(chunk_id)
            if document_id is not None:
                relevant_doc_ids.append(document_id)
        return relevant_chunk_ids, relevant_doc_ids

    def _get_expected_chunk_ids_and_docs(
        self, query: str
    ) -> tuple[list[str], list[str]]:
        expected_chunks = self.ground_truth[query].related_chunks
        expected_docs = self.ground_truth[query].related_docs
        return expected_chunks, expected_docs

    def _return_docs_and_chunks(
        self,
        retrieved_tuple: tuple[list[str], list[str]],
        expected_tuple: tuple[list[str], list[str]],
        query: str,
        top_k: int | None = None,
    ) -> tuple[tuple[list[str], list[str]], tuple[list[str], list[str]]]:
        retrieved_chunk_ids, retrieved_doc_ids = retrieved_tuple
        expected_chunk_ids, expected_doc_ids = expected_tuple
        if all(not lst for lst in [expected_chunk_ids, expected_doc_ids]):
            raise ValueError(
                f"No expected chunks or documents found for query '{query}'. Cannot compute metrics without expected data."
            )
        if top_k is not None and top_k > 0:
            retrieved_chunk_ids = retrieved_chunk_ids[:top_k]
            retrieved_doc_ids = retrieved_doc_ids[:top_k]
        return (retrieved_chunk_ids, retrieved_doc_ids), (
            expected_chunk_ids,
            expected_doc_ids,
        )

    def context_precision(
        self,
        retrieved_tuple: tuple[list[str], list[str]],
        expected_tuple: tuple[list[str], list[str]],
    ) -> float:
        retrieved_chunk_ids, retrieved_doc_ids = retrieved_tuple
        expected_chunk_ids, expected_doc_ids = expected_tuple
        if self.eval_level == 2 or not expected_chunk_ids:
            if not expected_chunk_ids:
                logger.warning(
                    "No chunks found. Using document IDs for precision calculation."
                )
            expected_chunk_ids = expected_doc_ids
            retrieved_chunk_ids = retrieved_doc_ids
        if not retrieved_chunk_ids:
            return 0.0
        relevant_ids = set(expected_chunk_ids)
        relevant_retrieved = sum(
            chunk_id in relevant_ids for chunk_id in retrieved_chunk_ids
        )
        return relevant_retrieved / len(retrieved_chunk_ids)

    def context_recall(
        self,
        retrieved_tuple: tuple[list[str], list[str]],
        expected_tuple: tuple[list[str], list[str]],
    ) -> float:
        retrieved_chunk_ids, retrieved_doc_ids = retrieved_tuple
        expected_chunk_ids, expected_doc_ids = expected_tuple
        if self.eval_level == 2 or not expected_chunk_ids:
            if not expected_chunk_ids:
                logger.warning(
                    "No chunks found. Using document IDs for recall calculation."
                )
            expected_chunk_ids = expected_doc_ids
            retrieved_chunk_ids = retrieved_doc_ids
        recall = (
            len(set(retrieved_chunk_ids) & set(expected_chunk_ids))
            / len(set(expected_chunk_ids))
            if expected_chunk_ids
            else 0.0
        )
        return recall

    def hit_rate(
        self,
        retrieved_tuple: tuple[list[str], list[str]],
        expected_tuple: tuple[list[str], list[str]],
    ) -> float:
        retrieved_chunk_ids, retrieved_doc_ids = retrieved_tuple
        expected_chunk_ids, expected_doc_ids = expected_tuple
        if self.eval_level == 2 or not expected_chunk_ids:
            if not expected_chunk_ids:
                logger.warning(
                    "No chunks found. Using document IDs for hit rate calculation."
                )
            expected_chunk_ids = expected_doc_ids
            retrieved_chunk_ids = retrieved_doc_ids
        hit_rate = int(bool(set(retrieved_chunk_ids) & set(expected_chunk_ids)))
        return hit_rate

    def _rr(
        self,
        retrieved_tuple: tuple[list[str], list[str]],
        expected_tuple: tuple[list[str], list[str]],
    ) -> float:
        retrieved_chunk_ids, _ = retrieved_tuple
        expected_chunk_ids, _ = expected_tuple
        if self.eval_level == 2 or not expected_chunk_ids:
            if not expected_chunk_ids:
                logger.warning(
                    "No chunks found. Using document IDs for RR calculation."
                )
            logger.warning(
                "Document-level evaluation is not compatible with RR calculation. Returning 0.0."
            )
            return 0.0
        rr_score = 0.0
        for rank, chunk_id in enumerate(retrieved_chunk_ids, start=1):
            if chunk_id in expected_chunk_ids:
                rr_score = 1.0 / rank
                break
        return rr_score

    def mrr(
        self,
        query_results: list[tuple[str, list[dict]]],
        top_k: int | None = None,
    ) -> float:
        if not query_results:
            logger.warning(
                "No query results provided for MRR calculation. MRR is undefined."
            )
            return 0.0
        mrr_score = 0.0
        for query, retrieved_chunks in query_results:
            query = super().validate_query(query, self.ground_truth)
            retrieved_tuple = self._get_chunk_ids_and_docs(retrieved_chunks)
            expected_tuple = self._get_expected_chunk_ids_and_docs(query)
            retrieved_tuple, expected_tuple = self._return_docs_and_chunks(
                retrieved_tuple, expected_tuple, query, top_k
            )
            rr = self._rr(retrieved_tuple, expected_tuple)
            mrr_score += rr
        return mrr_score / len(query_results)

    def binary_ndcg(
        self,
        retrieved_tuple: tuple[list[str], list[str]],
        expected_tuple: tuple[list[str], list[str]],
    ) -> float:
        retrieved_chunk_ids, _ = retrieved_tuple
        expected_chunk_ids, _ = expected_tuple
        if self.eval_level == 2 or not expected_chunk_ids:
            if not expected_chunk_ids:
                logger.warning(
                    "No chunks found. Using document IDs for NDCG calculation."
                )
            logger.warning(
                "Document-level evaluation is not compatible with NDCG calculation. Returning 0.0."
            )
            return 0.0
        dcg = 0.0
        idcg = 0.0
        for rank, chunk_id in enumerate(retrieved_chunk_ids, start=1):
            if chunk_id in expected_chunk_ids:
                dcg += 1.0 / math.log2(rank + 1)
        for rank in range(
            1, min(len(expected_chunk_ids), len(retrieved_chunk_ids)) + 1
        ):
            idcg += 1.0 / math.log2(rank + 1)
        ndcg_score = dcg / idcg if idcg > 0 else 0.0
        return ndcg_score

    def f1(
        self,
        retrieved_tuple: tuple[list[str], list[str]],
        expected_tuple: tuple[list[str], list[str]],
        query: str,
    ) -> float:
        precision = self.context_precision(retrieved_tuple, expected_tuple)
        recall = self.context_recall(retrieved_tuple, expected_tuple)
        if precision + recall == 0:
            logger.warning(
                f"Precision and Recall are both zero for query '{query}'. F1 score is undefined."
            )
            return 0.0
        f1_score = 2 * (precision * recall) / (precision + recall)
        return f1_score

    async def retrieve_and_rerank(
        self, top_k: int, max_concurrency: int = 5
    ) -> list[tuple[str, list[dict]]]:
        if max_concurrency <= 0:
            raise ValueError(f"max_concurrency must be positive, got {max_concurrency}")
        semaphore = asyncio.Semaphore(max_concurrency)
        queries = list(self.ground_truth.keys())

        async def retrieve_query(query: str) -> tuple[str, list[dict]] | None:
            try:
                async with semaphore:
                    await asyncio.sleep(0.1)
                    retrieved_chunks = await self.retriever.search(
                        query=query, top_k=top_k
                    )
                    reranked_chunks = await rerank_documents(
                        chain=self.reranker_chain,
                        query=query,
                        candidates=retrieved_chunks,
                        top_k=top_k,
                    )
                return query, [chunk.metadata for chunk in reranked_chunks]
            except RetrievalError as e:
                logger.error(f"Error retrieving results for query '{query}': {e}")
                return None

        tasks = []
        for query in queries:
            query = super().validate_query(query, self.ground_truth)
            task = asyncio.create_task(retrieve_query(query))
            tasks.append(task)
        results = []
        for task in asyncio.as_completed(tasks):
            result = await task
            if result is not None:
                results.append(result)
        return results

    async def evaluate(
        self,
        retrieval_top_k: int,
        evaluation_top_k: int | None = None,
        detailed_logs: bool = False,
        max_concurrency: int = 5,
    ) -> dict[str, dict[str, float]]:
        if retrieval_top_k <= 0:
            raise ValueError(f"Limit must be a positive integer, got {retrieval_top_k}")
        if await self.retriever.is_collection_exists(self.collection_name) is False:
            raise RetrievalError(
                f"Collection '{self.collection_name}' does not exist. Please ensure the collection is created and indexed before evaluation."
            )
        query_results = await self.retrieve_and_rerank(
            top_k=retrieval_top_k, max_concurrency=max_concurrency
        )
        len_query_results = len(query_results)
        if not query_results or len_query_results == 0:
            logger.warning(
                "No query results provided for evaluation. Returning empty metrics."
            )
            return RETRIEVAL_EVAL_RESULTS_SCHEMA
        total_precision = 0.0
        total_recall = 0.0
        total_hit_rate = 0.0
        total_ndcg = 0.0
        total_f1 = 0.0
        query_batch_size = 5
        for processed_queries, (query, retrieved_chunks) in enumerate(query_results):
            if (
                processed_queries % query_batch_size == 0
                or processed_queries == len_query_results
            ):
                logger.info(
                    f"Processed {processed_queries}/{len_query_results} queries for evaluation."
                )
            retrieved_tuple = self._get_chunk_ids_and_docs(retrieved_chunks)
            expected_tuple = self._get_expected_chunk_ids_and_docs(query)
            query = super().validate_query(query, self.ground_truth)
            retrieved_tuple, expected_tuple = self._return_docs_and_chunks(
                retrieved_tuple, expected_tuple, query, evaluation_top_k
            )
            total_precision += self.context_precision(retrieved_tuple, expected_tuple)
            total_recall += self.context_recall(retrieved_tuple, expected_tuple)
            total_hit_rate += self.hit_rate(retrieved_tuple, expected_tuple)
            total_ndcg += self.binary_ndcg(retrieved_tuple, expected_tuple)
            total_f1 += self.f1(retrieved_tuple, expected_tuple, query)
            if detailed_logs:
                logger.info(
                    f"Query: {query} | Precision@{evaluation_top_k}: {total_precision:.4f} | Recall@{evaluation_top_k}: {total_recall:.4f} | Hit Rate@{evaluation_top_k}: {total_hit_rate:.4f} | NDCG@{evaluation_top_k}: {total_ndcg:.4f} | F1@{evaluation_top_k}: {total_f1:.4f}"
                )
        num_queries = len(query_results)
        RETRIEVAL_EVAL_RESULTS_SCHEMA["Retrieval Effectiveness Metrics"][
            "precision"
        ] = (total_precision / num_queries)
        RETRIEVAL_EVAL_RESULTS_SCHEMA["Retrieval Effectiveness Metrics"]["recall"] = (
            total_recall / num_queries
        )
        RETRIEVAL_EVAL_RESULTS_SCHEMA["Retrieval Effectiveness Metrics"]["hit_rate"] = (
            total_hit_rate / num_queries
        )
        RETRIEVAL_EVAL_RESULTS_SCHEMA["Retrieval Effectiveness Metrics"]["f1"] = (
            total_f1 / num_queries
        )
        RETRIEVAL_EVAL_RESULTS_SCHEMA["Ranking Quality Metrics"]["mrr"] = self.mrr(
            query_results, evaluation_top_k
        )
        RETRIEVAL_EVAL_RESULTS_SCHEMA["Ranking Quality Metrics"]["ndcg"] = (
            total_ndcg / num_queries
        )
        logger.info(
            f"Evaluation Metrics @{evaluation_top_k if evaluation_top_k is not None else 'all'}: {RETRIEVAL_EVAL_RESULTS_SCHEMA}"
        )
        return RETRIEVAL_EVAL_RESULTS_SCHEMA
