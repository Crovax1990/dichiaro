"""Convert Italian-formatted number strings to Python float."""

import re


def parse_italian_number(text: str) -> float | None:
    if not text or not text.strip():
        return None
    text = text.strip().replace("\u00a0", "").replace(" ", "")
    text = re.sub(r"[^\d,.\-]", "", text)
    if not text:
        return None
    if text in (".", ",", "-", ""):
        return None
    has_dot = "." in text
    has_comma = "," in text
    if has_comma and has_dot:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif has_comma:
        if text.endswith(",00") or len(text) - text.rfind(",") - 1 <= 2:
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif has_dot:
        if text.endswith(".00") or len(text) - text.rfind(".") - 1 <= 2:
            text = text.replace(",", "").replace(".", ".")
        else:
            text = text.replace(".", "")
    try:
        return float(text)
    except ValueError:
        return None
