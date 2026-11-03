import asyncio
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar
from uuid import uuid4

from langchain.messages import HumanMessage, SystemMessage
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from lang_rag_playground.core.logger import get_logger
from lang_rag_playground.core.settings import settings
from lang_rag_playground.evaluation.evaluation_service import EvaluationService
from lang_rag_playground.models.agent_state_model import AgentState
from lang_rag_playground.models.context_model import Context
from lang_rag_playground.nodes.assistant_node import NOT_FOUND_ANSWER
from lang_rag_playground.prompts.prompts import (
    ANSWER_QUALITY_PROMPT,
    ANSWER_RELEVANCY_PROMPT,
    FAITHFULNESS_PROMPT,
)
from lang_rag_playground.schemas.generation_eval_schemas import (
    AnswerQualityEvalResponse,
    AnswerQualityScores,
    AnswerRelevancyEvalResponse,
    FaithfulnessEvalResponse,
)
from lang_rag_playground.services.llm import build_chat_model, build_embedding_model

logger = get_logger(__name__)

SchemaT = TypeVar("SchemaT", bound=BaseModel)


@dataclass
class GenerationRecord:
    question: str
    answer: str
    contexts: list[str]
    reference: str


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    if norm == 0:
        return 0.0
    similarity = dot / norm
    if not math.isfinite(similarity):
        raise ValueError("Cosine similarity must be finite.")
    return max(0.0, min(1.0, similarity))


class GenerationEvaluator(EvaluationService):
    EVAL_USER_ID = "evaluation_user"

    def __init__(
        self,
        graph: CompiledStateGraph[AgentState, Context, Any, Any],
        model_name: str = settings.GEMINI_JUDGE_MODEL,
        temperature: float = settings.EVALUATION_TEMPERATURE,
        ground_truth_path: Path | str = settings.GROUND_TRUTH_PATH,
        factual_weight: float = 0.75,
        semantic_weight: float = 0.25,
    ):
        super().__init__(ground_truth_path)
        for name, weight in {
            "factual_weight": factual_weight,
            "semantic_weight": semantic_weight,
        }.items():
            if not math.isfinite(weight) or not 0 <= weight <= 1:
                raise ValueError(f"{name} must be a finite number between 0 and 1.")
        total_weight = factual_weight + semantic_weight
        if total_weight <= 0:
            raise ValueError("At least one weight must be greater than zero.")
        self.factual_weight = factual_weight / total_weight
        self.semantic_weight = semantic_weight / total_weight
        self.graph = graph
        self.llm = build_chat_model(model_name, temperature)
        self.embeddings = build_embedding_model()

    async def _structured_call(
        self, prompt: str, content: str, schema: type[SchemaT]
    ) -> SchemaT:
        response = await self.llm.with_structured_output(schema).ainvoke(
            [SystemMessage(content=prompt), HumanMessage(content=content)]
        )
        if not isinstance(response, schema):
            raise TypeError(f"The response is not of type {schema.__name__} class.")
        return response

    async def faithfulness(self, answer: str, contexts: list[str]) -> float:
        if not contexts:
            logger.warning("No contexts were retrieved; faithfulness is 0.0.")
            return 0.0
        response = await self._structured_call(
            FAITHFULNESS_PROMPT,
            f"Asistanın cevabı: {answer}\nAsistanın alıntıladığı metinler: {contexts}",
            FaithfulnessEvalResponse,
        )
        valid_claims = []
        for claim in response.claims:
            if (claim.claim_type, claim.classification) in {
                ("supported", "TP"),
                ("unsupported", "FP"),
            }:
                valid_claims.append(claim)
            else:
                logger.warning(
                    f"Skipping inconsistent faithfulness claim "
                    f"({claim.claim_type}/{claim.classification}): {claim.claim}"
                )
        if not valid_claims:
            return 0.0
        supported = sum(claim.classification == "TP" for claim in valid_claims)
        return supported / len(valid_claims)

    async def answer_relevancy(self, question: str, answer: str) -> float:
        response = await self._structured_call(
            ANSWER_RELEVANCY_PROMPT,
            f"Kullanıcı sorusu: {question}\nDeğerlendirilecek asistanın cevap: {answer}",
            AnswerRelevancyEvalResponse,
        )
        generated_questions = response.generated_questions
        vectors = await self.embeddings.aembed_documents(
            [question] + [q.question for q in generated_questions]
        )
        if len(vectors) != len(generated_questions) + 1:
            raise ValueError("Embedder returned an unexpected number of vectors.")
        question_vector, *generated_vectors = vectors
        score = sum(
            _cosine_similarity(question_vector, vector)
            for generated_question, vector in zip(generated_questions, generated_vectors)
            if generated_question.is_relevant
        )
        return score / len(generated_questions)

    async def answer_quality(
        self, question: str, answer: str, expected_answer: str
    ) -> AnswerQualityScores:
        response = await self._structured_call(
            ANSWER_QUALITY_PROMPT,
            f"Kullanıcı sorusu: {question}\nAsistanın cevabı: {answer}\nBeklenen cevap: {expected_answer}",
            AnswerQualityEvalResponse,
        )
        claims = response.claims
        tp = sum(c.classification == "TP" for c in claims)
        fp = sum(c.classification == "FP" for c in claims)
        fn = sum(c.classification == "FN" for c in claims)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        factual_f1 = (
            2 * precision * recall / (precision + recall) if precision + recall else 0.0
        )
        vectors = await self.embeddings.aembed_documents([answer, expected_answer])
        if len(vectors) != 2:
            raise ValueError("Embedder must return two vectors.")
        semantic_score = _cosine_similarity(vectors[0], vectors[1])
        return AnswerQualityScores(
            correctness=self.factual_weight * factual_f1
            + self.semantic_weight * semantic_score,
            completeness=recall,
            accuracy=factual_f1,
        )

    async def get_answer(self, question: str, reference: str) -> GenerationRecord:
        state = await self.graph.ainvoke(
            {"messages": [HumanMessage(content=question)]},
            config={"configurable": {"thread_id": f"eval-{uuid4()}"}},
            context=Context(user_id=self.EVAL_USER_ID),
        )
        sources = state.get("reranked_documents") or []
        return GenerationRecord(
            question=question,
            answer=state.get("generation") or "",
            contexts=[doc.page_content for doc in sources],
            reference=reference,
        )

    async def score(self, record: GenerationRecord) -> dict[str, float]:
        if not record.answer.strip():
            logger.warning(f"Empty answer for question '{record.question}'; scoring 0.")
            return dict.fromkeys(
                [
                    "faithfulness_score",
                    "answer_relevancy_score",
                    "answer_correctness_score",
                    "completeness_score",
                    "answer_accuracy_score",
                ],
                0.0,
            )
        faithfulness, relevancy, quality = await asyncio.gather(
            self.faithfulness(record.answer, record.contexts),
            self.answer_relevancy(record.question, record.answer),
            self.answer_quality(record.question, record.answer, record.reference),
        )
        return {
            "faithfulness_score": faithfulness,
            "answer_relevancy_score": relevancy,
            "answer_correctness_score": quality.correctness,
            "completeness_score": quality.completeness,
            "answer_accuracy_score": quality.accuracy,
        }

    async def evaluate(self, max_concurrency: int = 3) -> dict[str, dict[str, float]]:
        if max_concurrency <= 0:
            raise ValueError(f"max_concurrency must be positive, got {max_concurrency}")
        if not self.ground_truth:
            raise ValueError("No questions found in ground truth for evaluation.")
        semaphore = asyncio.Semaphore(max_concurrency)

        async def evaluate_question(
            question: str, reference: str
        ) -> tuple[GenerationRecord, dict[str, float]] | None:
            try:
                async with semaphore:
                    record = await self.get_answer(question, reference)
                    scores = await self.score(record)
            except Exception as e:
                logger.error(f"Error evaluating question '{question}': {e}")
                return None
            logger.info(f"Question: {question} | {scores}")
            return record, scores

        results = [
            result
            for result in await asyncio.gather(
                *(
                    evaluate_question(question, gt.answer)
                    for question, gt in self.ground_truth.items()
                )
            )
            if result is not None
        ]
        if not results:
            raise RuntimeError("Every question failed during generation evaluation.")
        metrics = {
            name: sum(scores[name] for _, scores in results) / len(results)
            for name in results[0][1]
        }
        metrics["not_found_rate"] = sum(
            record.answer.strip() == NOT_FOUND_ANSWER for record, _ in results
        ) / len(results)
        evaluation_results = {
            "Generation Evaluation Metrics": metrics,
            "Run Summary": {
                "evaluated_questions": float(len(results)),
                "failed_questions": float(len(self.ground_truth) - len(results)),
            },
        }
        logger.info(f"Generation Evaluation Metrics: {evaluation_results}")
        return evaluation_results
