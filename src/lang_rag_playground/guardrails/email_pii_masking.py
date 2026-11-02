import re

from langchain.agents.middleware import PIIMatch

_TEXT_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
EMAIL_MASK = "[EMAIL]"


def email_detector(content: str) -> list[PIIMatch]:
    if content is None or not isinstance(content, str) or not content.strip():
        return []
    content = content.strip()
    matches = []
    for match in _TEXT_EMAIL_RE.finditer(content):
        candidate = re.sub(r"\s", "", match.group())
        matches.append(
            PIIMatch(
                type="EMAIL",
                value=candidate,
                start=match.start(),
                end=match.end(),
            )
        )
    return matches
