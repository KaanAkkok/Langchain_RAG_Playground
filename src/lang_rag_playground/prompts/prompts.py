from pathlib import Path

from lang_rag_playground.core.settings import settings

INTENT_PROMPT = Path(settings.INTENT_PROMPT_PATH).read_text(encoding="utf-8")
RERANK_PROMPT = Path(settings.RERANKER_PROMPT_PATH).read_text(encoding="utf-8")
ASSISTANT_PROMPT = Path(settings.ASSISTANT_PROMPT_PATH).read_text(encoding="utf-8")
ASSISTANT_AGENT_PROMPT = Path(settings.ASSISTANT_AGENT_PROMPT_PATH).read_text(encoding="utf-8")
JUDGE_PROMPT = Path(settings.JUDGE_PROMPT_PATH).read_text(encoding="utf-8")
MEMORY_PROMPT = Path(settings.MEMORY_PROMPT_PATH).read_text(encoding="utf-8")