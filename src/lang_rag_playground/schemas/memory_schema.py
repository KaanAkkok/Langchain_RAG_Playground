from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MemoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    memory_type: Literal[
        "fact", "event", "preference", "goal", "inference"
    ] = Field(
        ...,
        description="The type of memory, e.g., 'fact', 'event', 'preference', 'goal' or 'inference'",
    )
    content: str = Field(..., description="The summary of the memory")
    inference: str | None = Field(
        ..., description="Inference or conclusion drawn from the memory"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence level of the inference"
    )


class MemoryExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    memories: list[MemoryResponse] = Field(
        ...,
        description="Long-term memories extracted from the conversation; empty if nothing worth remembering",
    )