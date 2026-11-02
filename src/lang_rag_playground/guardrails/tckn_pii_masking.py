import re

from langchain.agents.middleware import PIIMatch

_TEXT_TC_RE = re.compile(r"\b[1-9]\d{10}\b")
TCKN_MASK = "[TCKN]"


def tckn_detector(content: str) -> list[PIIMatch]:
    if content is None or not isinstance(content, str) or not content.strip():
        return []
    content = content.strip()
    matches = []
    for match in _TEXT_TC_RE.finditer(content):
        candidate = re.sub(r"\s", "", match.group())
        if _is_tckn_valid(candidate):
            matches.append(
                PIIMatch(
                    type="TCKN",
                    value=candidate,
                    start=match.start(),
                    end=match.end(),
                )
            )
    return matches


def _is_tckn_valid(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    if len(digits) != 11 or digits[0] == "0":
        return False
    digits = list(map(int, digits))
    odd_sum = sum(digits[i] for i in range(0, 9, 2))
    even_sum = sum(digits[i] for i in range(1, 8, 2))
    check_digit_10 = (odd_sum * 7 - even_sum) % 10
    check_digit_11 = (sum(digits[:10])) % 10
    return check_digit_10 == digits[9] and check_digit_11 == digits[10]
