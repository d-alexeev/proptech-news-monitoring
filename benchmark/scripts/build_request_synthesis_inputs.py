#!/usr/bin/env python3
"""Build Phase 2 request-synthesis inputs from reviewed selection notes."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = ROOT / "benchmark" / "datasets" / "request-synthesis"
PHASE1_INPUTS_PATH = ROOT / "benchmark" / "datasets" / "request-article-retrieval" / "inputs.jsonl"
SELECTION_NOTES_PATH = DATASET_DIR / "selection_notes.json"
OUTPUT_PATH = DATASET_DIR / "inputs.jsonl"

CASE_ID = "syn-nd-001"
SOURCE_RETRIEVAL_CASE_ID = "reqret-001"
ARTICLE_COUNT = 12
MIN_FULL_TEXT_CHARS = 1500
SOFT_CAP_FULL_TEXT_CHARS = 20000
ARTICLE_FIELDS = {
    "article_id",
    "body_excerpt",
    "body_full_text",
    "normalized_url",
    "published",
    "title",
}
FORBIDDEN_MODEL_MARKERS = ("Local NML", "Fetch failed", "Paywall", "\u26a0\ufe0f")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def clean_markdown_article(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
    text = text.strip()
    text = re.sub(r"\A# .+?\n+", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def ensure_clean_model_text(article_id: str, field_name: str, text: str) -> None:
    for marker in FORBIDDEN_MODEL_MARKERS:
        if marker in text:
            raise ValueError(f"{article_id} {field_name} contains forbidden marker {marker!r}")


def build_inputs() -> dict[str, Any]:
    phase1_cases = read_jsonl(PHASE1_INPUTS_PATH)
    phase1_case = next(case for case in phase1_cases if case["id"] == SOURCE_RETRIEVAL_CASE_ID)
    phase1_by_id = {article["article_id"]: article for article in phase1_case["corpus"]}

    selection_notes = read_json(SELECTION_NOTES_PATH)
    selected = selection_notes["selected_articles"]
    if len(selected) != ARTICLE_COUNT:
        raise ValueError(f"expected {ARTICLE_COUNT} selected articles, got {len(selected)}")

    articles: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for item in selected:
        article_id = item["article_id"]
        phase1_article = phase1_by_id[article_id]
        source_path = ROOT / item["full_text_source_path"]
        body_full_text = clean_markdown_article(source_path.read_text(encoding="utf-8"))
        body_excerpt = phase1_article["body_excerpt"]

        if len(body_full_text) < MIN_FULL_TEXT_CHARS:
            raise ValueError(f"{article_id} body_full_text shorter than policy minimum")
        if len(body_full_text) > SOFT_CAP_FULL_TEXT_CHARS:
            raise ValueError(f"{article_id} body_full_text exceeds policy soft cap")
        if len(body_full_text) != item["full_text_char_count"]:
            raise ValueError(f"{article_id} full_text_char_count mismatch")
        ensure_clean_model_text(article_id, "body_excerpt", body_excerpt)
        ensure_clean_model_text(article_id, "body_full_text", body_full_text)

        normalized_url = phase1_article["normalized_url"]
        if normalized_url in seen_urls:
            raise ValueError(f"duplicate normalized_url {normalized_url}")
        seen_urls.add(normalized_url)

        card = {
            "article_id": article_id,
            "body_excerpt": body_excerpt,
            "body_full_text": body_full_text,
            "normalized_url": normalized_url,
            "published": phase1_article.get("published"),
            "title": phase1_article.get("title"),
        }
        if set(card) != ARTICLE_FIELDS:
            raise ValueError(f"{article_id} unexpected article fields")
        articles.append(card)

    return {
        "article_set_size": ARTICLE_COUNT,
        "articles": articles,
        "id": CASE_ID,
        "source_retrieval_case_id": SOURCE_RETRIEVAL_CASE_ID,
        "user_request": phase1_case["user_request"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()

    record = build_inputs()
    args.output.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
