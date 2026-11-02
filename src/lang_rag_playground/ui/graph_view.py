from collections.abc import Sequence

LEGEND_MARKDOWN = (
    "**Durum:** "
    "🟨 Çalışıyor · "
    "🟩 Tamamlandı · "
    "🟥 Hata · "
    "--> Koşullu yönlendirme (router)"
)

_CLASS_DEFS = (
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
        if node and node not in (active_node, failed_node) and node not in visited_clean:
            visited_clean.append(node)

    if visited_clean:
        lines.append(f"\tclass {','.join(visited_clean)} visited;")
    if active_node and active_node != failed_node:
        lines.append(f"\tclass {active_node} active;")
    if failed_node:
        lines.append(f"\tclass {failed_node} failed;")

    diagram = "\n".join(lines)
    return f"```mermaid\n{diagram}\n```\n\n{LEGEND_MARKDOWN}"
