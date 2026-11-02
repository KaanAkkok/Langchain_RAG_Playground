import re

from langchain.agents.middleware import PIIMatch

_TEXT_IBAN_RE = re.compile(r"\bTR\s?\d{2}(?:\s?\d{4}){5}\s?\d{2}\b", re.IGNORECASE)
IBAN_MASK = "[IBAN]"


def iban_detector(content: str) -> list[PIIMatch]:
    if content is None or not isinstance(content, str) or not content.strip():
        return []
    content = content.strip()
    matches = []
    for match in _TEXT_IBAN_RE.finditer(content):
        candidate = re.sub(r"\s", "", match.group())
        if _is_iban_valid(candidate):
            matches.append(
                PIIMatch(
                    type="IBAN",
                    value=candidate,
                    start=match.start(),
                    end=match.end(),
                )
            )
    return matches


def _is_iban_valid(value: str) -> bool:
    iban = re.sub(r"\s+", "", value).upper()
    if not iban.startswith("TR") or len(iban) != 26:
        return False
    rearranged = iban[4:] + iban[:4]
    numeric_iban = ""
    for char in rearranged:
        if char.isdigit():
            numeric_iban += char
        elif char.isalpha():
            numeric_iban += str(ord(char) - 55)
        else:
            return False
    return int(numeric_iban) % 97 == 1
