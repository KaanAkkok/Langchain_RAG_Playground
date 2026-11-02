import ipaddress
import re

from langchain.agents.middleware import PIIMatch

_TEXT_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
IP_MASK = "[IP]"


def ip_detector(content: str) -> list[PIIMatch]:
    if content is None or not isinstance(content, str) or not content.strip():
        return []
    content = content.strip()
    matches = []
    for match in _TEXT_IP_RE.finditer(content):
        candidate = re.sub(r"\s", "", match.group())
        if _is_ip_valid(candidate):
            matches.append(
                PIIMatch(
                    type="IP",
                    value=candidate,
                    start=match.start(),
                    end=match.end(),
                )
            )
    return matches


def _is_ip_valid(value: str) -> bool:
    try:
        ipaddress.ip_address(value.strip())
        return True
    except ValueError:
        return False
