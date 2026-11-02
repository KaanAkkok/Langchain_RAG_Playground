from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Intent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    intent: Literal[
        "knowledge_question",
        "chitchat",
        "out_of_scope",
        "needs_clarification",
    ] = Field(..., description="The intent of the user's query.")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="The confidence score of the intent classification.",
    )
    resolved_query: str = Field(
        ..., description="The query after any necessary clarification."
    )
