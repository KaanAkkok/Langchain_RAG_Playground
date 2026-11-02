import re

from langchain.agents.middleware import PIIMatch

_TEXT_BIRTH_DATE_RE = re.compile(
    r"(?i)\b(?:do[gğ]um\s*tarihi|do[gğ]um\s*g[uü]n[uü])\s*[:=]?\s*\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b",
    re.IGNORECASE,
)
BIRTH_DATE_MASK = "[BIRTH_DATE]"


def birth_date_detector(content: str) -> list[PIIMatch]:
    if content is None or not isinstance(content, str) or not content.strip():
        return []
    content = content.strip()
    matches = []
    for match in _TEXT_BIRTH_DATE_RE.finditer(content):
        candidate = re.sub(r"\s", "", match.group())
        matches.append(
            PIIMatch(
                type="BIRTH_DATE",
                value=candidate,
                start=match.start(),
                end=match.end(),
            )
        )
    return matches
