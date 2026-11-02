from lang_rag_playground.ui.graph_view import render

SAMPLE_MERMAID = "graph TD;\n\t__start__ --> input_guardrails;\n\tinput_guardrails --> intent;\n"


def test_render_base_diagram_includes_mermaid_block_and_legend():
    out = render(SAMPLE_MERMAID)
    assert "```mermaid" in out
    assert "input_guardrails" in out
    assert "Çalışıyor" in out and "Tamamlandı" in out and "Hata" in out


def test_render_applies_precedence_failed_over_active_over_visited():
    out = render(
        SAMPLE_MERMAID,
        active_node="assistant",
        visited=["input_guardrails", "intent", "assistant", "judge"],
        failed_node="judge",
    )
    assert "class assistant active;" in out
    assert "class judge failed;" in out
    assert "class input_guardrails,intent visited;" in out
    assert "class assistant visited;" not in out
    assert "class judge visited;" not in out


def test_render_same_active_and_failed_emits_only_failed_and_deduplicates_visited():
    out = render(
        SAMPLE_MERMAID,
        active_node="assistant",
        visited=["input_guardrails", "intent", "input_guardrails", "assistant"],
        failed_node="assistant",
    )
    assert "class assistant failed;" in out
    assert "class assistant active;" not in out
    assert "class input_guardrails,intent visited;" in out

