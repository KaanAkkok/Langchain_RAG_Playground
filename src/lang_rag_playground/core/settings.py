import os
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_project_root() -> Path:
    configured_root = os.getenv("PROJECT_ROOT")
    if configured_root:
        return Path(configured_root).resolve()

    module_path = Path(__file__).resolve()
    for parent in module_path.parents:
        if (parent / "pyproject.toml").is_file():
            return parent

    return Path.cwd().resolve()


PROJECT_ROOT = _find_project_root()
PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", env_file_encoding="utf-8"
    )

    LOG_LEVEL: str = "INFO"

    SUPPORTED_FILE_TYPES: list[str] = [".pdf"]

    GEMINI_API_KEY: SecretStr = SecretStr(os.getenv("GEMINI_API_KEY", ""))
    GEMINI_EMBEDDING_MODEL: str = ""
    GEMINI_CHAT_MODEL: str = ""

    GEMINI_INTENT_MODEL: str = ""
    GEMINI_RERANKER_MODEL: str = ""
    GEMINI_ASSISTANT_MODEL: str = ""
    GEMINI_JUDGE_MODEL: str = ""
    GEMINI_MEMORY_MODEL: str = ""

    INTENT_PROMPT_PATH: str = str(PROMPTS_DIR / "INTENT_PROMPT.md")
    RERANKER_PROMPT_PATH: str = str(PROMPTS_DIR / "RERANKER_PROMPT.md")
    ASSISTANT_PROMPT_PATH: str = str(PROMPTS_DIR / "ASSISTANT_PROMPT.md")
    TOOL_PROMPT_PATH: str = str(PROMPTS_DIR / "TOOL_PROMPT.md")
    JUDGE_PROMPT_PATH: str = str(PROMPTS_DIR / "JUDGE_PROMPT.md")
    MEMORY_PROMPT_PATH: str = str(PROMPTS_DIR / "MEMORY_PROMPT.md")
    FAITHFULNESS_PROMPT_PATH: str = str(PROMPTS_DIR / "FAITHFULNESS_PROMPT.md")
    ANSWER_RELEVANCY_PROMPT_PATH: str = str(PROMPTS_DIR / "ANSWER_RELEVANCY_PROMPT.md")
    ANSWER_QUALITY_PROMPT_PATH: str = str(PROMPTS_DIR / "ANSWER_QUALITY_PROMPT.md")
    ANSWER_QUALITY_PROMPT_PATH: str = str(PROMPTS_DIR / "ANSWER_QUALITY_PROMPT.md")
    ANSWER_RELEVANCY_PROMPT_PATH: str = str(PROMPTS_DIR / "ANSWER_RELEVANCY_PROMPT.md")
    FAITHFULNESS_PROMPT_PATH: str = str(PROMPTS_DIR / "FAITHFULNESS_PROMPT.md")

    INTENT_TEMPERATURE: float = Field(default=0.0, ge=0.0, le=1.0)
    RERANKER_TEMPERATURE: float = Field(default=0.0, ge=0.0, le=1.0)
    ASSISTANT_TEMPERATURE: float = Field(default=0.0, ge=0.0, le=1.0)
    JUDGE_TEMPERATURE: float = Field(default=0.0, ge=0.0, le=1.0)
    MEMORY_TEMPERATURE: float = Field(default=0.0, ge=0.0, le=1.0)
    EVALUATION_TEMPERATURE: float = Field(default=0.0, ge=0.0, le=1.0)

    VECTORDB_KNOWLEDGE_COLLECTION_NAME: str = "knowledge_base"
    VECTORDB_MEMORY_COLLECTION_NAME: str = "memory_base"
    VECTORDB_EVALUATION_COLLECTION_NAME: str = "evaluation_base"
    RETRIEVAL_EVALUATION_LEVEL: Literal[1, 2] = 1
    EVAL_SNAPSHOT_PATH: str = str(
        PROJECT_ROOT
        / "data"
        / "evaluation"
        / "snapshots"
        / "EVALUATION_SNAPSHOT.snapshot"
    )
    EVALUATION_DOCUMENTS_DIR: str = str(
        PROJECT_ROOT
        / "data"
        / "evaluation"
        / "documents"
    )
    GROUND_TRUTH_PATH: str = str(
        PROJECT_ROOT
        / "data"
        / "evaluation"
        / "ground_truth"
        / "GROUND_TRUTH.json"
    )
    GROUNDTRUTH_CHUNK_ID_TAG: str = "chunk_id"
    GROUNDTRUTH_DOCUMENT_ID_TAG: str = "document_name"

    INTENT_MIN_CONFIDENCE: float = Field(default=0.5, ge=0.0, le=1.0)
    MIN_RERANK_SCORE: float = 3.0
    JUDGE_MAX_RETRIES: int = 3
    LLM_MAX_ATTEMPTS: int = Field(default=3, ge=1)
    RERANK_CANDIDATES: int = 10
    TOP_K_CANDIDATES: int = 5
    MAX_TOOL_CALLS: int = Field(default=2, ge=0, le=3)
    TOOL_MAX_RETRIES: int = Field(default=2, ge=0, le=3)

    EMBED_BATCH_SIZE: int = 10
    MAX_CHUNK_CHARS: int = 1200
    MIN_CHUNK_CHARS: int = 200
    OVERLAP_CHARS: int = 100
    BREAK_PERCENTILE: float = 90
    MAX_HISTORY_TOKENS: int = 2000

    SEMANTIC_CHUNKER_BUFFER_SIZE: int = Field(default=1, ge=0, le=5)

    LONG_TERM_MEMORY_BATCH_SIZE: int = 10
    LONG_TERM_MEMORY_SEARCH_LIMIT: int = 5
    LONG_TERM_MEMORY_CONFIDENCE_THRESHOLD: float = 0.7
    LONG_TERM_MEMORY_MIN_SCORE: float = 0.1

    RAW_DOCUMENTS_DIR: str = str(PROJECT_ROOT / "data" / "documents" / "raw_documents")
    SAVED_DOCUMENTS_DIR: str = str(PROJECT_ROOT / "data" / "documents" / "saved_documents")

    QDRANT_API_KEY: SecretStr = SecretStr(os.getenv("QDRANT_API_KEY", ""))
    QDRANT_PATH: str = str(PROJECT_ROOT / "data" / "qdrant")
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_GRPC_PORT: int = 6334

    GRADIO_HOST: str = "localhost"
    GRADIO_PORT: int = 7860

    @model_validator(mode="after")
    def be_sure_dirs(self):
        os.makedirs(self.RAW_DOCUMENTS_DIR, exist_ok=True)
        os.makedirs(self.SAVED_DOCUMENTS_DIR, exist_ok=True)
        os.makedirs(self.EVALUATION_DOCUMENTS_DIR, exist_ok=True)
        return self


settings = Settings()
