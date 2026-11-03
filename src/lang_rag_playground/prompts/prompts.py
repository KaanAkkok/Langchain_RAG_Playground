from pathlib import Path

from lang_rag_playground.core.settings import settings

INTENT_PROMPT = Path(settings.INTENT_PROMPT_PATH).read_text(encoding="utf-8")
RERANK_PROMPT = Path(settings.RERANKER_PROMPT_PATH).read_text(encoding="utf-8")
ASSISTANT_PROMPT = Path(settings.ASSISTANT_PROMPT_PATH).read_text(encoding="utf-8")
TOOL_PROMPT = Path(settings.TOOL_PROMPT_PATH).read_text(
    encoding="utf-8"
)
JUDGE_PROMPT = Path(settings.JUDGE_PROMPT_PATH).read_text(encoding="utf-8")
MEMORY_PROMPT = Path(settings.MEMORY_PROMPT_PATH).read_text(encoding="utf-8")
FAITHFULNESS_PROMPT = Path(settings.FAITHFULNESS_PROMPT_PATH).read_text(
    encoding="utf-8"
)
ANSWER_RELEVANCY_PROMPT = Path(settings.ANSWER_RELEVANCY_PROMPT_PATH).read_text(
    encoding="utf-8"
)
ANSWER_QUALITY_PROMPT = Path(settings.ANSWER_QUALITY_PROMPT_PATH).read_text(
    encoding="utf-8"
)
ANSWER_QUALITY_PROMPT = Path(settings.ANSWER_QUALITY_PROMPT_PATH).read_text(encoding="utf-8")
ANSWER_RELEVANCY_PROMPT = Path(settings.ANSWER_RELEVANCY_PROMPT_PATH).read_text(encoding="utf-8")
FAITHFULNESS_PROMPT = Path(settings.FAITHFULNESS_PROMPT_PATH).read_text(encoding="utf-8")
