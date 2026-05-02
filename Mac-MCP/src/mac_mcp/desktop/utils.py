import re

_PRIVATE_USE_RE = re.compile(r"[-\U000f0000-\U000fffff\U00100000-\U0010ffff]")


def remove_private_use_chars(text: str) -> str:
    """Strip Unicode Private Use Area characters that can cause display issues."""
    return _PRIVATE_USE_RE.sub("", text)
