"""Normalize extracted values: strip €/%, convert to int/float, preserve strings."""

import re


def normalize_value(raw: str):
    """Convert a raw extracted string to its appropriate Python type."""
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None

    raw = raw.replace("\u00a0", " ").replace("\xa0", " ")

    # Strip trailing € or % for detection
    has_euro = raw.endswith("€")
    has_percent = raw.endswith("%")
    clean = raw.rstrip("€%").strip()

    # If it's purely numeric (possibly with . or , or -)
    numeric_pattern = re.match(r"^-?[\d.,]+$", clean)
    if numeric_pattern:
        # Keep as string if leading zero and no separators (date, CF, ID codes)
        if "." not in clean and "," not in clean and clean.startswith("0"):
            return clean
        return _parse_number(clean)

    # If it's a date-like string (DDMMYYYY)
    if re.match(r"^\d{8}$", clean):
        return clean

    # If it contains digits but also letters (like "00967720285" or "B507")
    if any(c.isdigit() for c in clean) and any(c.isalpha() for c in clean):
        return clean

    # Pure letters or mixed
    return clean


def _parse_number(s: str) -> int | float:
    """Parse italian-formatted number string to Python number."""
    s = s.strip()
    if not s:
        return 0

    has_dot = "." in s
    has_comma = "," in s

    if has_comma and has_dot:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif has_comma:
        if s.endswith(",00") or (len(s) - s.rfind(",") - 1) >= 1:
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif has_dot:
        if s.endswith(".00") or (len(s) - s.rfind(".") - 1) <= 2:
            pass
        else:
            s = s.replace(".", "")

    val = float(s)
    if val == int(val):
        return int(val)
    return val
