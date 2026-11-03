from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator


class GroundTruth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., description="The question to be answered.")
    answer: str = Field(..., description="The expected answer to the question.")
    related_docs: list[str] = Field(
        ..., description="List of document IDs related to the question."
    )
    related_chunks: list[str] = Field(
        ..., description="List of chunk IDs related to the question."
    )
    expected_keywords: list[str] = Field(
        ..., description="List of keywords expected in the answer."
    )

    @field_validator("question", "answer", "expected_keywords", mode="before")
    def strip_and_lower(cls, value):
        if isinstance(value, str):
            return value.strip().lower()
        elif isinstance(value, list):
            return [v.strip().lower() for v in value]
        return value


class ModifiedGroundTruth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    related_docs: list[str]
    related_chunks: list[str]
    expected_keywords: list[str]


class ModifiedGroundTruthCollection(RootModel[dict[str, ModifiedGroundTruth]]):
    pass
