from collections.abc import Sequence
from html import escape

LEGEND_HTML = (
    '<p><strong>Durum:</strong> '
    "🟨 Çalışıyor · "
    "🟩 Tamamlandı · "
    "🟥 Hata</p>"
)

_CLASS_DEFS = (
    "\tclassDef default fill:#f2f0ff,stroke:#7c6fd6,color:#111827;\n"
    "\tclassDef first fill:#f2f0ff,fill-opacity:1,color:#111827;\n"
    "\tclassDef last fill:#bfb6fc,color:#111827;\n"
    "\tclassDef active fill:#fde68a,stroke:#d97706,stroke-width:2px,color:#1f2937;\n"
    "\tclassDef visited fill:#bbf7d0,stroke:#16a34a,stroke-width:2px,color:#14532d;\n"
    "\tclassDef failed fill:#fecaca,stroke:#dc2626,stroke-width:2px,color:#7f1d1d;"
)


def render(
    base_mermaid: str,
    active_node: str | None = None,
    visited: Sequence[str] = (),
    failed_node: str | None = None,
) -> str:
    lines = [base_mermaid.rstrip(), _CLASS_DEFS]

    visited_clean: list[str] = []
    for node in visited:
        if (
            node
            and node not in (active_node, failed_node)
            and node not in visited_clean
        ):
            visited_clean.append(node)

    if visited_clean:
        lines.append(f"\tclass {','.join(visited_clean)} visited;")
    if active_node and active_node != failed_node:
        lines.append(f"\tclass {active_node} active;")
    if failed_node:
        lines.append(f"\tclass {failed_node} failed;")

    diagram = escape("\n".join(lines))
    return f'<div class="mermaid">{diagram}</div>{LEGEND_HTML}'
