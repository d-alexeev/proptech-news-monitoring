#!/usr/bin/env python3
from __future__ import annotations

import re
from typing import Any


ENGLISH_MARKERS = [
    "Top Signals",
    "Worth Tracking",
    "Evidence note",
    "Avito lens",
    "Source:",
    "Read Next",
]

MIN_RELEVANT_CHARS = 80
MIN_CYRILLIC_RATIO = 0.55


def _strip_noise(text: str) -> str:
    cleaned = re.sub(r"https?://\S+", " ", text or "")
    cleaned = re.sub(r"\[[^\]]+\]\([^)]*\)", " ", cleaned)
    cleaned = re.sub(r"`[^`]*`", " ", cleaned)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"mode:\s*[a-z_]+\s*\|\s*\d{2}\.\d{2}\.\d{4}", " ", cleaned, flags=re.I)
    return cleaned


def check_russian_text(text: str, *, field_path: str) -> dict[str, Any]:
    cleaned = _strip_noise(text)
    cyrillic_chars = len(re.findall(r"[А-Яа-яЁё]", cleaned))
    latin_chars = len(re.findall(r"[A-Za-z]", cleaned))
    relevant_chars = cyrillic_chars + latin_chars
    markers = [marker for marker in ENGLISH_MARKERS if marker.lower() in (text or "").lower()]
    ratio = cyrillic_chars / relevant_chars if relevant_chars else 0.0
    if relevant_chars < MIN_RELEVANT_CHARS and not markers:
        status = "skip"
    elif markers or ratio < MIN_CYRILLIC_RATIO:
        status = "fail"
    else:
        status = "pass"
    return {
        "status": status,
        "field_path": field_path,
        "cyrillic_chars": cyrillic_chars,
        "latin_chars": latin_chars,
        "cyrillic_ratio": ratio,
        "english_markers": markers,
    }


def require_russian_text(text: str, *, field_path: str) -> None:
    result = check_russian_text(text, field_path=field_path)
    if result["status"] == "fail":
        raise ValueError(
            "Russian language gate failed for "
            f"{field_path}: ratio={result['cyrillic_ratio']:.2f}, "
            f"markers={result['english_markers']}"
        )
