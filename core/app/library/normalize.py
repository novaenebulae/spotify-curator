from __future__ import annotations

import re
import unicodedata


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    text = value.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\s+", " ", text)
    return text.strip()
