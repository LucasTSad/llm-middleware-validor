from __future__ import annotations

import unicodedata

from prompt_validator.core.contracts import GuardConfig, NormalizedText

_INVISIBLE_CODEPOINTS = {
    "\u200b",  # ZERO WIDTH SPACE
    "\ufeff",  # ZERO WIDTH NO-BREAK SPACE
    "\u00ad",  # SOFT HYPHEN
    "\u202e",  # RIGHT-TO-LEFT OVERRIDE
    "\u2060",  # WORD JOINER
}


def normalize(original: str, config: GuardConfig) -> NormalizedText:

    if not config.normalize_input:
        return NormalizedText(
            original=original,
            normalized=original,
            offset_map=tuple(range(len(original))),
        )

    normalized_chars: list[str] = []
    offset_map: list[int] = []

    for i, char in enumerate(original):
        if char not in _INVISIBLE_CODEPOINTS:
            normalized_text = unicodedata.normalize("NFKC", char)
            normalized_chars.extend(normalized_text)
            offset_map.extend([i] * len(normalized_text))

    clean_text = "".join(normalized_chars)

    return NormalizedText(
        original=original, normalized=clean_text, offset_map=tuple(offset_map)
    )
