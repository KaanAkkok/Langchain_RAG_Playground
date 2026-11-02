from pydantic import BaseModel, ConfigDict, Field


class JudgeSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    faithfulness: bool = Field(
        ..., description="Whether the answer is faithful to the provided context."
    )
    relevancy: bool = Field(
        ..., description="Whether the answer is relevant to the question."
    )
    hallucination: bool = Field(
        ..., description="Whether the answer contains hallucinated information."
    )
    nsfw: bool = Field(..., description="Whether the answer contains NSFW content.")
    contain_sensitive_info: bool = Field(
        ..., description="Whether the answer contains sensitive information."
    )
    feedback: str | None = Field(
        ...,
        description="Feedback or comments regarding the answer; use null when there is no feedback.",
    )
