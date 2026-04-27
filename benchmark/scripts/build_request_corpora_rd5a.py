#!/usr/bin/env python3
"""Build RD5a draft corpora for reqret-001 and reqret-002."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = ROOT / "benchmark" / "RD-PLANS.md"
DATASET_DIR = ROOT / "benchmark" / "datasets" / "request-article-retrieval"
INVENTORY_PATH = DATASET_DIR / "candidate_inventory.json"
DISCOVERY_PATH = DATASET_DIR / "candidate_discovery_draft.json"

DEFAULT_CASES = ["reqret-001", "reqret-002"]
TARGET_CORPUS_SIZE = 50
MIN_DISTRACTOR_RATIO = 0.30


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compact_text(value: Any, limit: int = 900) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        value = " ".join(str(item) for item in value)
    text = re.sub(r"\s+", " ", str(value)).strip()
    if not text:
        return None
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def extract_request_text(case_id: str) -> str:
    plan = PLAN_PATH.read_text(encoding="utf-8")
    pattern = rf"### {re.escape(case_id)}[^\n]*\n\n(?P<body>.*?)(?=\n### reqret-|\n## Dataset Contract)"
    match = re.search(pattern, plan, flags=re.S)
    if not match:
        raise ValueError(f"request seed not found for {case_id}")
    return match.group("body").strip()


def candidate_card(candidate: dict[str, Any]) -> dict[str, Any]:
    optional_fields = [
        "analyst_summary",
        "why_it_matters",
        "avito_implication",
        "topic_tags",
        "event_type",
        "priority_score",
        "companies",
    ]
    card = {
        "article_id": candidate["article_id"],
        "normalized_url": candidate["normalized_url"],
        "title": candidate.get("title"),
        "source_id": candidate.get("source_id"),
        "source_name": candidate.get("source_name"),
        "published": candidate.get("published"),
        "url": candidate.get("url"),
        "lead_or_summary": compact_text(candidate.get("lead_or_summary")),
        "body_excerpt": compact_text(candidate.get("body_excerpt")),
        "provenance": candidate.get("provenance", []),
    }
    for field in optional_fields:
        value = candidate.get(field)
        if value not in (None, "", []):
            card[field] = value
    return card


def flatten_groups(case_discovery: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    return {group: list(items) for group, items in case_discovery["groups"].items()}


def build_case_selection(case_discovery: dict[str, Any]) -> tuple[list[str], dict[str, list[str]]]:
    groups = flatten_groups(case_discovery)
    selected_ids: list[str] = []
    selected_set: set[str] = set()
    selected_by_group = {
        "likely_relevant": [],
        "possible": [],
        "distractor": [],
        "reject": [],
    }

    quotas = {
        "likely_relevant": 15,
        "possible": 17,
        "distractor": 18,
        "reject": 0,
    }

    for group_name, limit in quotas.items():
        for item in groups[group_name]:
            if item["article_id"] in selected_set:
                continue
            selected_ids.append(item["article_id"])
            selected_set.add(item["article_id"])
            selected_by_group[group_name].append(item["article_id"])
            if len(selected_by_group[group_name]) >= limit:
                break

    fallback_order = ["distractor", "possible", "likely_relevant", "reject"]
    while len(selected_ids) < TARGET_CORPUS_SIZE:
        added = False
        for group_name in fallback_order:
            for item in groups[group_name]:
                if item["article_id"] in selected_set:
                    continue
                selected_ids.append(item["article_id"])
                selected_set.add(item["article_id"])
                selected_by_group[group_name].append(item["article_id"])
                added = True
                break
            if len(selected_ids) >= TARGET_CORPUS_SIZE:
                break
        if not added:
            break

    return selected_ids[:TARGET_CORPUS_SIZE], selected_by_group


def corpus_window(corpus: list[dict[str, Any]]) -> str:
    dates = sorted(
        item["published"]
        for item in corpus
        if isinstance(item.get("published"), str) and re.match(r"\d{4}-\d{2}-\d{2}", item["published"])
    )
    if not dates:
        return "unknown"
    return f"{dates[0]}..{dates[-1]}"


def build_corpora(case_ids: list[str], milestone: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    inventory = load_json(INVENTORY_PATH)
    discovery = load_json(DISCOVERY_PATH)
    candidates_by_id = {item["article_id"]: item for item in inventory["candidates"]}

    inputs = []
    notes: dict[str, Any] = {
        "schema_version": "corpus_selection_notes_v1",
        "benchmark_id": "request-article-retrieval",
        "milestone": milestone,
        "case_ids": case_ids,
        "selection_policy": {
            "target_corpus_size": TARGET_CORPUS_SIZE,
            "minimum_distractor_ratio": MIN_DISTRACTOR_RATIO,
            "source": "candidate_discovery_draft.json",
            "note": "Selection notes are review metadata and are not model input.",
        },
        "cases": {},
    }

    for case_id in case_ids:
        selected_ids, selected_by_group = build_case_selection(discovery["requests"][case_id])
        corpus = [candidate_card(candidates_by_id[article_id]) for article_id in selected_ids]
        distractor_count = len(selected_by_group["distractor"])
        inputs.append(
            {
                "id": case_id,
                "user_request": extract_request_text(case_id),
                "corpus_window": corpus_window(corpus),
                "source_scope": sorted(
                    {
                        provenance
                        for item in corpus
                        for provenance in item.get("provenance", [])
                    }
                ),
                "corpus": corpus,
            }
        )
        notes["cases"][case_id] = {
            "corpus_size": len(corpus),
            "distractor_count": distractor_count,
            "distractor_ratio": round(distractor_count / len(corpus), 4),
            "selected_article_ids_by_discovery_group": selected_by_group,
        }

    return inputs, notes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--inputs-output",
        default="benchmark/datasets/request-article-retrieval/inputs.jsonl",
        help="Path to write clean benchmark input JSONL.",
    )
    parser.add_argument(
        "--notes-output",
        default="benchmark/datasets/request-article-retrieval/corpus_selection_notes.json",
        help="Path to write corpus selection review notes.",
    )
    parser.add_argument(
        "--case",
        action="append",
        dest="case_ids",
        help="Case id to include. Repeat for multiple cases. Defaults to RD5a cases.",
    )
    parser.add_argument(
        "--milestone",
        default="RD5a",
        help="Milestone label to write into corpus selection notes.",
    )
    args = parser.parse_args()

    case_ids = args.case_ids or DEFAULT_CASES
    inputs, notes = build_corpora(case_ids, args.milestone)
    inputs_path = Path(args.inputs_output)
    notes_path = Path(args.notes_output)
    if not inputs_path.is_absolute():
        inputs_path = ROOT / inputs_path
    if not notes_path.is_absolute():
        notes_path = ROOT / notes_path

    inputs_path.write_text(
        "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in inputs),
        encoding="utf-8",
    )
    notes_path.write_text(
        json.dumps(notes, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "wrote "
        f"{inputs_path.relative_to(ROOT)} and {notes_path.relative_to(ROOT)} "
        f"for {', '.join(case_ids)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
