from dataclasses import dataclass


@dataclass
class Citation:
    chunk_id: str = ""
    page: int = 0
    paragraph_no: int = 0
    document_name: str = ""
    document_path: str = ""
    section_title: str = ""
    text: str = ""
    score: float = 0.0
    reranker_score: float = 0.0
