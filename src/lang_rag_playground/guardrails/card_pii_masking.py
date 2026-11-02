import re

from langchain.agents.middleware import PIIMatch

_TEXT_CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
CARD_MASK = "[CARD]"


def card_detector(content: str) -> list[PIIMatch]:
    if content is None or not isinstance(content, str) or not content.strip():
        return []
    content = content.strip()
    matches = []
    for match in _TEXT_CARD_RE.finditer(content):
        candidate = re.sub(r"[\s-]", "", match.group())
        if _is_luhn_valid(candidate):
            matches.append(
                PIIMatch(
                    type="CARD",
                    value=candidate,
                    start=match.start(),
                    end=match.end(),
                )
            )
    return matches


def _is_luhn_valid(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    if not 13 <= len(digits) <= 19:
        return False
    checksum = 0
    parity = len(digits) % 2
    for index, digit in enumerate(map(int, digits)):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0
