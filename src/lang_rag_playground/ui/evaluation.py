from collections.abc import AsyncIterator
from typing import Any

import gradio as gr

from lang_rag_playground.core.logger import get_logger
from lang_rag_playground.evaluation.eval import run_eval
from lang_rag_playground.ui.services import AppServices

logger = get_logger(__name__)

EVAL_TABLE_HEADERS = ["Grup", "Metrik", "Değer"]

_GROUP_LABELS = {
    "Retrieval Effectiveness Metrics": "Retrieval",
    "Ranking Quality Metrics": "Ranking",
    "Generation Evaluation Metrics": "Generation",
    "Run Summary": "Özet",
}


def results_to_rows(
    results: dict[str, dict[str, dict[str, float]]],
) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for groups in results.values():
        for group, metrics in groups.items():
            label = _GROUP_LABELS.get(group, group)
            for name, value in metrics.items():
                shown = int(value) if float(value).is_integer() and value > 1 else round(value, 3)
                rows.append([label, name, shown])
    return rows


def graph_label(services: AppServices) -> str:
    return services.graph_builder.__name__


async def run_evaluation(
    services: AppServices,
) -> AsyncIterator[tuple[str, Any, dict[str, Any]]]:
    yield (
        f"[EVALUATING ...]`{graph_label(services)}` değerlendiriliyor. "
        "Retrieval + generation birkaç dakika sürebilir...",
        gr.update(),
        gr.update(interactive=False),
    )
    try:
        results = await run_eval(
            vector_store=services.vectordb,
            graph_builder=services.graph_builder,
            guardrails_service=services.guardrails,
        )
    except Exception as e:
        logger.exception("Evaluation failed.")
        yield f"[EVALUATION FAILED] Değerlendirme başarısız: {e}", gr.update(), gr.update(interactive=True)
        return
    yield (
        f"[EVALUATION COMPLETE] `{graph_label(services)}` değerlendirmesi tamamlandı.",
        results_to_rows(results),
        gr.update(interactive=True),
    )
