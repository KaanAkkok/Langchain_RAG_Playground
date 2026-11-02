import re

from langchain.agents.middleware import PIIMatch

_TEXT_PLATE_RE = re.compile(
    r"(?<![\w])(?:0[1-9]|[1-7]\d|8[01])\s?[A-Z]{1,3}\s?\d{2,4}(?![\w])", re.IGNORECASE
)
PLATE_MASK = "[PLATE]"


def plate_detector(content: str) -> list[PIIMatch]:
    if content is None or not isinstance(content, str) or not content.strip():
        return []
    content = content.strip()
    matches = []
    for match in _TEXT_PLATE_RE.finditer(content):
        candidate = re.sub(r"\s", "", match.group())
        matches.append(
            PIIMatch(
                type="PLATE",
                value=candidate,
                start=match.start(),
                end=match.end(),
            )
        )
    return matches
