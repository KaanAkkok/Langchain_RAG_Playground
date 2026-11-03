from typing import Literal

from lang_rag_playground.core.settings import settings
from lang_rag_playground.models.agent_state_model import AgentState


def route_after_input_guardrails(state: AgentState) -> Literal["blocked", "intent"]:
    """Girdi guardrail'inden sonra bir sonraki dugumu secer.

    Girdi: state["is_input_safe"] (bool, yoksa guvensiz say).
    Cikti: "blocked" veya "intent".
    Adimlar:
      1. is_input_safe False/yoksa -> "blocked"
      2. Aksi halde -> "intent"
    """
    # TODO (Görev 6): Öğrenci Rehberi > Görev 6
    # Adım 1: state.get("is_input_safe") yoksa veya False ise "blocked" dön.
    # Adım 2: Aksi halde "intent" dön.
    raise NotImplementedError("TODO (Görev 6): Öğrenci Rehberi > Görev 6")


# Workflow graph only: the agentic graph lets the assistant decide whether to search.
def route_after_memory_recall(state: AgentState) -> Literal["retrieval", "assistant"]:
    """Hafiza cagirmadan sonra bir sonraki dugumu secer (sadece workflow graph).

    Girdi: state["intent"] (str).
    Cikti: "retrieval" veya "assistant".
    Adimlar:
      1. intent == "knowledge_question" -> "retrieval"
      2. Aksi halde -> "assistant"
    """
    # TODO (Görev 6): Öğrenci Rehberi > Görev 6
    # Adım 1: intent "knowledge_question" ise "retrieval" dön.
    # Adım 2: Aksi halde "assistant" dön.
    raise NotImplementedError("TODO (Görev 6): Öğrenci Rehberi > Görev 6")


def route_after_judge(
    state: AgentState,
    max_retries: int = settings.JUDGE_MAX_RETRIES,
) -> Literal["blocked", "output_guardrails", "assistant"]:
    """Judge dugumunden sonra bir sonraki dugumu secer.

    Girdi: judge_blocked, judge_passed, retry_count (state), max_retries.
    Cikti: "blocked", "output_guardrails" veya "assistant".
    Adimlar:
      1. judge_blocked -> "blocked"
      2. judge_passed -> "output_guardrails"
      3. retry_count >= max_retries -> "output_guardrails" (hak bitti)
      4. Aksi halde -> "assistant" (yeniden dene)
    """
    # TODO (Görev 6): Öğrenci Rehberi > Görev 6
    # Adım 1-4: yukaridaki karar sirasini uygula (sira onemli).
    raise NotImplementedError("TODO (Görev 6): Öğrenci Rehberi > Görev 6")


def route_after_output_guardrails(
    state: AgentState, batch_size: int = settings.LONG_TERM_MEMORY_BATCH_SIZE
) -> Literal["memory_extract", "__end__"]:
    """Cikti guardrail'inden sonra bir sonraki dugumu secer.

    Girdi: state["messages"], batch_size.
    Cikti: "memory_extract" veya "__end__".
    Adimlar:
      1. Mesaj sayisi batch_size'a tam bolunuyorsa -> "memory_extract"
      2. Aksi halde -> "__end__"
    """
    # TODO (Görev 6): Öğrenci Rehberi > Görev 6
    # Adım 1: len(state["messages"]) % batch_size == 0 ise "memory_extract" dön.
    # Adım 2: Aksi halde "__end__" dön.
    raise NotImplementedError("TODO (Görev 6): Öğrenci Rehberi > Görev 6")
