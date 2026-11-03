import os
from pathlib import Path

from pydantic import Field, SecretStr
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
    ASSISTANT_AGENT_PROMPT_PATH: str = str(PROMPTS_DIR / "ASSISTANT_AGENT_PROMPT.md")
    JUDGE_PROMPT_PATH: str = str(PROMPTS_DIR / "JUDGE_PROMPT.md")
    MEMORY_PROMPT_PATH: str = str(PROMPTS_DIR / "MEMORY_PROMPT.md")

    INTENT_TEMPERATURE: float = Field(default=0.0, ge=0.0, le=1.0)
    RERANKER_TEMPERATURE: float = Field(default=0.0, ge=0.0, le=1.0)
    ASSISTANT_TEMPERATURE: float = Field(default=0.0, ge=0.0, le=1.0)
    JUDGE_TEMPERATURE: float = Field(default=0.0, ge=0.0, le=1.0)
    MEMORY_TEMPERATURE: float = Field(default=0.0, ge=0.0, le=1.0)

    VECTORDB_KNOWLEDGE_COLLECTION_NAME: str = "knowledge_base"
    VECTORDB_MEMORY_COLLECTION_NAME: str = "memory_base"
    EVAL_SNAPSHOT_PATH: str = str(
        PROJECT_ROOT
        / "data"
        / "evaluation"
        / "snapshots"
        / "EVALUATION_SNAPSHOT.snapshot"
    )

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
    LONG_TERM_MEMORY_MIN_SCORE: float = 0.5

    RAW_DOCUMENTS_DIR: str = str(PROJECT_ROOT / "data" / "raw_documents")
    SAVED_DOCUMENTS_DIR: str = str(PROJECT_ROOT / "data" / "saved_documents")

    QDRANT_API_KEY: SecretStr = SecretStr(os.getenv("QDRANT_API_KEY", ""))
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333

    GRADIO_HOST: str = "localhost"
    GRADIO_PORT: int = 7860


settings = Settings()
