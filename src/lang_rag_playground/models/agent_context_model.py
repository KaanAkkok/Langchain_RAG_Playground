from dataclasses import dataclass, field

from langchain_core.documents import Document


@dataclass
class AgentContext:
    sources: list[Document] = field(default_factory=list)
