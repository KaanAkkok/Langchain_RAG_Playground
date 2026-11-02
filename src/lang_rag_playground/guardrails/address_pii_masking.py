import re

from langchain.agents.middleware import PIIMatch

_TEXT_ADDRESS_RE = re.compile(
    r"(?i)\b(?:adresim|ikamet\s*adresim|ev\s*adresim)\s*[:=]?\s*[^\n.!?]{3,160}",
    re.IGNORECASE,
)
ADDRESS_MASK = "[ADDRESS]"


def address_detector(content: str) -> list[PIIMatch]:
    if content is None or not isinstance(content, str) or not content.strip():
        return []
    content = content.strip()
    matches = []
    for match in _TEXT_ADDRESS_RE.finditer(content):
        candidate = re.sub(r"\s", "", match.group())
        matches.append(
            PIIMatch(
                type="ADDRESS",
                value=candidate,
                start=match.start(),
                end=match.end(),
            )
        )
    return matches
