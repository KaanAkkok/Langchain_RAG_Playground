from pydantic import BaseModel, ConfigDict, Field


class RerankItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int = Field(ge=0, description="The ID of the document.")
    score: float = Field(ge=0, le=10, description="The rerank score for the document.")


class RerankResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scores: list[RerankItem] = Field(
        description="List of rerank scores for the retrieved documents."
    )
