from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# =========================== CLAIM SCHEMA ===========================


class ClaimSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim: str = Field(..., description="The claim made in the answer.")
    claim_type: Literal["supported", "unsupported"] = Field(
        ..., description="The type of the claim."
    )
    classification: Literal["TP", "FP", "FN"] = Field(
        description=(
            "TP: İddia hem cevapta hem referansta mevcut."
            "FP: İddia cevapta mevcut ama referansta yok."
            "FN: İddia referansta mevcut ama cevapta yok."
        )
    )

    @field_validator("claim", mode="before")
    def strip_and_lower(cls, value):
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("claim_type", mode="before")
    def validate_claim_type(cls, value):
        if value not in ["supported", "unsupported"]:
            raise ValueError(
                f"Invalid claim type: {value}. Must be one of 'supported' or 'unsupported'."
            )
        return value

    @field_validator("classification", mode="before")
    def validate_classification(cls, value):
        if value not in ["TP", "FP", "FN"]:
            raise ValueError(
                f"Invalid classification: {value}. Must be one of 'TP', 'FP', or 'FN'."
            )
        return value


# =========================== FAITHFULNESS EVALUATION SCHEMAS ===========================


class FaithfulnessEvalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claims: list[ClaimSchema] = Field(..., description="The claims made in the answer.")


# =========================== ANSWER RELEVANCY EVALUATION SCHEMAS ===========================


class GeneratedQuestionSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(..., min_length=1, description="The generated question.")
    is_relevant: bool = Field(
        ..., description="Whether the generated question is relevant to the answer."
    )

    @field_validator("question", mode="before")
    def strip_and_lower(cls, value):
        if isinstance(value, str):
            return value.strip().lower()
        return value


class AnswerRelevancyEvalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    generated_questions: list[GeneratedQuestionSchema] = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Exactly three questions generated from the answer.",
    )


# =========================== ANSWER QUALITY EVALUATION SCHEMAS ===========================


class AnswerQualityScores(BaseModel):
    correctness: float
    completeness: float
    accuracy: float


class AnswerQualityEvalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claims: list[ClaimSchema] = Field(..., description="The claims made in the answer.")
    is_correct: bool = Field(
        ..., description="Whether the answer is correct based on the expected answer."
    )
