import re

from langchain.agents.middleware import PIIMatch

_TEXT_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?90[- ]?)?(?:0[- ]?)?5\d{2}[- ]?\d{3}[- ]?\d{2}[- ]?\d{2}(?!\d)"
)
PHONE_MASK = "[PHONE]"


def phone_detector(content: str) -> list[PIIMatch]:
    if content is None or not isinstance(content, str) or not content.strip():
        return []
    content = content.strip()
    matches = []
    for match in _TEXT_PHONE_RE.finditer(content):
        candidate = re.sub(r"[- \s]", "", match.group())
        matches.append(
            PIIMatch(
                type="PHONE",
                value=candidate,
                start=match.start(),
                end=match.end(),
            )
        )
    return matches
