"""Cyrillic → Latin transliteration for display to clients."""

from __future__ import annotations

import re

# Common Cyrillic → Latin (Polish/ISO-like for PL context)
_CYRILLIC_TO_LATIN = {
    "а": "a", "б": "b", "в": "v", "г": "g", "ґ": "g", "д": "d", "е": "e", "є": "ie",
    "ж": "zh", "з": "z", "и": "y", "і": "i", "ї": "i", "й": "i", "к": "k", "л": "l",
    "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "",
    "ы": "y", "ь": "", "э": "e", "ю": "iu", "я": "a",
    # uppercase
    "А": "A", "Б": "B", "В": "V", "Г": "G", "Ґ": "G", "Д": "D", "Е": "E", "Є": "Ie",
    "Ж": "Zh", "З": "Z", "И": "Y", "І": "I", "Ї": "I", "Й": "I", "К": "K", "Л": "L",
    "М": "M", "Н": "N", "О": "O", "П": "P", "Р": "R", "С": "S", "Т": "T", "У": "U",
    "Ф": "F", "Х": "Kh", "Ц": "Ts", "Ч": "Ch", "Ш": "Sh", "Щ": "Shch", "Ъ": "",
    "Ы": "Y", "Ь": "", "Э": "E", "Ю": "Iu", "Я": "Ya",
}

_CYRILLIC_PATTERN = re.compile(r"[\u0400-\u04FF\u0500-\u052F]")


def has_cyrillic(text: str | None) -> bool:
    """Return True if text contains Cyrillic characters."""
    if not text:
        return False
    return bool(_CYRILLIC_PATTERN.search(text))


def transliterate(text: str | None) -> str:
    """
    Transliterate Cyrillic to Latin.
    Non-Cyrillic characters are preserved.
    """
    if not text:
        return ""
    return "".join(_CYRILLIC_TO_LATIN.get(c, c) for c in text)
