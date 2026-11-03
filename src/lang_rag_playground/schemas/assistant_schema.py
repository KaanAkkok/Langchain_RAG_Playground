from pydantic import BaseModel, Field


# add model_config extra ignore if u using workflow graph rather than agent graph
# Because in agent graph assistant calls tools and gemini reject additionalProperties
class AssistantResponse(BaseModel):
    answer: str = Field(
        ...,
        description="The answer to the user, with inline source references such as [1] or [1][3].",
    )
    cited_sources: list[int] = Field(
        default_factory=list,
        description="The numbers of the sources referenced in the answer (e.g. [1, 3]). Empty if no source was used.",
    )
