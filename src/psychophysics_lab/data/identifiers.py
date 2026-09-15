"""Portable validation for acquisition directory components."""

import re
import unicodedata

_RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])$", re.IGNORECASE)


def validate_path_component(value: str, *, label: str) -> str:
    """Reject unsafe names without silently renaming acquisition identifiers."""
    text = str(value)
    if not text or not text.strip() or text in {".", ".."}:
        raise ValueError(f"{label} folder component must be a nonempty name.")
    if text.endswith((" ", ".")):
        raise ValueError(f"{label} must not end with a space or dot.")
    if any(char in '<>:"/\\|?*' for char in text):
        raise ValueError(f"{label} contains a Windows-invalid filename character.")
    if any(unicodedata.category(char) == "Cc" for char in text):
        raise ValueError(f"{label} contains a control character.")
    if _RESERVED.fullmatch(text.split(".", 1)[0].rstrip(" ")):
        raise ValueError(f"{label} is a reserved Windows filename.")
    return text
