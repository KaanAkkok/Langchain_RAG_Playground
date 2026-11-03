import re

from langchain.agents.middleware import PIIMatch

_TEXT_NAME_RE = re.compile(
    r"\b(?i:ad[iı]m|ismim|ad[iı]\s*soyad[iı]m|isim\s*soyisim|soyad[iı]m)"
    r"\s*[:=]?\s+[A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜa-zçğıöşü'-]+"
    r"(?:\s+[A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜa-zçğıöşü'-]+){0,3}",
)
NAME_MASK = "[NAME]"


def name_detector(content: str) -> list[PIIMatch]:
    if content is None or not isinstance(content, str) or not content.strip():
        return []
    content = content.strip()
    matches = []
    for match in _TEXT_NAME_RE.finditer(content):
        candidate = re.sub(r"\s", "", match.group())
        matches.append(
            PIIMatch(
                type="NAME",
                value=candidate,
                start=match.start(),
                end=match.end(),
            )
        )
    return matches
