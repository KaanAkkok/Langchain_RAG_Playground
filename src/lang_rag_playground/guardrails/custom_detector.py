import re

from langchain.agents.middleware import PIIMatch


def custom_detector(content: str, regex_patterns: list[re.Pattern]) -> list[PIIMatch]:
    if content is None or not isinstance(content, str) or not content.strip():
        return []
    if (
        regex_patterns is None
        or not isinstance(regex_patterns, list)
        or not all(isinstance(pattern, re.Pattern) for pattern in regex_patterns)
    ):
        return []
    content = content.strip()
    matches = []
    for pattern in regex_patterns:
        for match in pattern.finditer(content):
            candidate = re.sub(r"\s", "", match.group())
            matches.append(
                PIIMatch(
                    type="CUSTOM",
                    value=candidate,
                    start=match.start(),
                    end=match.end(),
                )
            )
    return matches
