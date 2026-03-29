import re

_INJECTION_PATTERNS = re.compile(
    r"(ignore previous|disregard|system prompt|you are now|act as|jailbreak)",
    re.IGNORECASE,
)


def sanitize(text: str) -> str:
    return _INJECTION_PATTERNS.sub("[removed]", text).strip()
