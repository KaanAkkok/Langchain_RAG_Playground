import json
from pathlib import Path

from lang_rag_playground.core.exceptions import InvalidGroundTruthSchemaError
from lang_rag_playground.core.logger import get_logger
from lang_rag_playground.schemas.ground_truth_schema import (
    GroundTruth,
    ModifiedGroundTruth,
    ModifiedGroundTruthCollection,
)

logger = get_logger(__name__)


class EvaluationService:
    def __init__(self, ground_truth_path: Path | str):
        self.ground_truth = {
            query: gt
            for collection in self.validate_ground_truth(ground_truth_path)
            for query, gt in collection.root.items()
        }

    @staticmethod
    def validate_query(query: str, ground_truth: dict) -> str:
        if not isinstance(query, str):
            raise TypeError(f"Query must be a string, got {type(query)}")
        query = query.strip().lower()
        if not query:
            raise ValueError("Query cannot be empty or whitespace")
        if query not in ground_truth:
            raise ValueError(f"Query '{query}' not found in ground truth")
        return query

    @staticmethod
    def validate_ground_truth(
        ground_truth_path: Path | str,
    ) -> list[ModifiedGroundTruthCollection]:
        if isinstance(ground_truth_path, str):
            ground_truth_path = Path(ground_truth_path)
        if not ground_truth_path.exists():
            raise FileNotFoundError(f"Ground truth file not found: {ground_truth_path}")
        try:
            with open(ground_truth_path, "r", encoding="utf-8") as f:
                ground_truth = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Error decoding JSON from ground truth file: {ground_truth_path}. Error: {e}"
            )
        prepared_ground_truth = []
        for item in ground_truth:
            if not isinstance(item, dict):
                raise TypeError(
                    f"Each ground truth item must be a dictionary, got {type(item)}"
                )
            try:
                gt = GroundTruth(**item)
            except InvalidGroundTruthSchemaError as e:
                raise InvalidGroundTruthSchemaError(
                    f"Invalid ground truth item: {item}. Error: {e}"
                )
            gt.question = gt.question.strip().lower()
            payload = {
                gt.question: ModifiedGroundTruth(
                    answer=gt.answer,
                    related_docs=gt.related_docs,
                    related_chunks=gt.related_chunks,
                    expected_keywords=gt.expected_keywords,
                )
            }
            try:
                mgt = ModifiedGroundTruthCollection(root=payload)
            except InvalidGroundTruthSchemaError as e:
                logger.error(
                    f"Error validating modified ground truth for question '{gt.question}': {e}"
                )
                raise InvalidGroundTruthSchemaError(
                    f"Invalid modified ground truth item: {payload}. Error: {e}"
                )
            prepared_ground_truth.append(mgt)
        return prepared_ground_truth
