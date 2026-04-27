#!/usr/bin/env python3
"""Run RD7 agent-side QA for request retrieval draft labels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = ROOT / "benchmark" / "datasets" / "request-article-retrieval"
INPUTS_PATH = DATASET_DIR / "inputs.jsonl"
GOLDEN_PATH = DATASET_DIR / "golden.jsonl"
DISCOVERY_PATH = DATASET_DIR / "candidate_discovery_draft.json"
NOTES_PATH = DATASET_DIR / "corpus_selection_notes.json"

KEYWORD_TRAPS = {
    "reqret-001": [
        "art_18162cc3a6",
        "art_7a641278d2",
        "art_6b7b3fd7b1",
    ],
    "reqret-002": [
        "art_6dd0cbd6be",
        "art_905093b4eb",
        "art_58952c33fa",
    ],
    "reqret-003": [
        "art_58952c33fa",
        "art_f064d3ecb3",
        "art_af0c575579",
    ],
    "reqret-004": [
        "art_538020fa38",
        "art_905093b4eb",
        "art_58952c33fa",
    ],
}

DRAFT_STATUS_BY_CASE = {
    "reqret-001": "draft_rd6a",
    "reqret-002": "draft_rd6a",
    "reqret-003": "draft_rd6b",
    "reqret-004": "draft_rd6b",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def bucket_map(record: dict[str, Any]) -> dict[str, str]:
    mapping = {}
    for bucket in ["must_find", "nice_to_have", "borderline", "irrelevant"]:
        for article_id in record[bucket]:
            mapping[article_id] = bucket
    return mapping


def article_map(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {article["article_id"]: article for article in case["corpus"]}


def find_discovery_item(discovery_case: dict[str, Any], article_id: str) -> dict[str, Any] | None:
    for items in discovery_case["groups"].values():
        for item in items:
            if item["article_id"] == article_id:
                return item
    return None


def compact_item(
    item: dict[str, Any],
    bucket: str,
    qa_decision: str,
) -> dict[str, Any]:
    return {
        "article_id": item["article_id"],
        "title": item.get("title"),
        "bucket": bucket,
        "score": item.get("score"),
        "matched_facets": item.get("matched_facets", []),
        "provenance": item.get("provenance", []),
        "qa_decision": qa_decision,
    }


def rejected_sample(discovery_case: dict[str, Any], buckets: dict[str, str]) -> list[dict[str, Any]]:
    sample = []
    for item in discovery_case["groups"]["reject"][:10]:
        bucket = buckets.get(item["article_id"], "not_in_corpus")
        if bucket in {"must_find", "nice_to_have"}:
            decision = "discovery_false_negative_already_caught_in_golden"
        elif bucket == "borderline":
            decision = "borderline_discovery_false_negative_marked_for_expert_review"
        else:
            decision = "no_false_negative_signal"
        sample.append(compact_item(item, bucket, decision))
    return sample


def raw_only_review(discovery_case: dict[str, Any], buckets: dict[str, str]) -> dict[str, Any]:
    reviewed = []
    flags = []
    for group, items in discovery_case["groups"].items():
        for item in items:
            provenance = item.get("provenance", [])
            is_raw_only = "article_md" not in provenance and any(
                value.startswith("raw_") for value in provenance
            )
            if not is_raw_only:
                continue
            bucket = buckets.get(item["article_id"], "not_in_corpus")
            decision = "reviewed_no_change"
            if bucket == "not_in_corpus" and item.get("score", 0) >= 2:
                decision = "potential_raw_only_false_negative_for_expert_review"
            elif bucket in {"must_find", "nice_to_have"}:
                decision = "raw_only_relevance_captured_in_golden"
            reviewed.append(
                {
                    **compact_item(item, bucket, decision),
                    "discovery_group": group,
                }
            )
            if decision == "potential_raw_only_false_negative_for_expert_review":
                flags.append(reviewed[-1])
    return {
        "reviewed_count": len(reviewed),
        "flag_count": len(flags),
        "flags": flags,
    }


def keyword_trap_review(
    case_id: str,
    articles: dict[str, dict[str, Any]],
    buckets: dict[str, str],
) -> list[dict[str, Any]]:
    traps = []
    for article_id in KEYWORD_TRAPS[case_id]:
        article = articles[article_id]
        bucket = buckets[article_id]
        traps.append(
            {
                "article_id": article_id,
                "title": article.get("title"),
                "bucket": bucket,
                "provenance": article.get("provenance", []),
                "qa_decision": "valid_keyword_or_same_theme_trap"
                if bucket == "irrelevant"
                else "trap_candidate_needs_expert_review",
            }
        )
    return traps


def corpus_difficulty(record: dict[str, Any], notes_case: dict[str, Any]) -> dict[str, Any]:
    relevant_count = len(record["must_find"]) + len(record["nice_to_have"])
    corpus_size = (
        len(record["must_find"])
        + len(record["nice_to_have"])
        + len(record["borderline"])
        + len(record["irrelevant"])
    )
    relevant_ratio = relevant_count / corpus_size
    distractor_ratio = notes_case["distractor_ratio"]
    status = "not_too_easy"
    if relevant_ratio > 0.45 or distractor_ratio < 0.30:
        status = "revision_recommended"
    return {
        "corpus_size": corpus_size,
        "must_find_count": len(record["must_find"]),
        "nice_to_have_count": len(record["nice_to_have"]),
        "borderline_count": len(record["borderline"]),
        "irrelevant_count": len(record["irrelevant"]),
        "relevant_ratio": round(relevant_ratio, 4),
        "distractor_ratio": distractor_ratio,
        "status": status,
    }


def build_review() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    inputs = {case["id"]: case for case in load_jsonl(INPUTS_PATH)}
    golden_records = load_jsonl(GOLDEN_PATH)
    discovery = load_json(DISCOVERY_PATH)
    notes = load_json(NOTES_PATH)

    review = {
        "schema_version": "agent_qa_review_v1",
        "benchmark_id": "request-article-retrieval",
        "milestone": "RD7",
        "review_type": "agent_side_qa",
        "expert_review_status": "expert_review_pending",
        "scope_note": (
            "This is an agent-side QA pass authorized as a substitute artifact "
            "for RD7. It does not claim final project-team human adjudication."
        ),
        "cases": {},
        "summary": {
            "cases_reviewed": len(golden_records),
            "critical_blockers": 0,
            "expert_review_pending": True,
        },
    }

    updated_golden = []
    for record in golden_records:
        case_id = record["id"]
        buckets = bucket_map(record)
        articles = article_map(inputs[case_id])
        discovery_case = discovery["requests"][case_id]
        notes_case = notes["cases"][case_id]
        rejected = rejected_sample(discovery_case, buckets)
        raw_review = raw_only_review(discovery_case, buckets)
        traps = keyword_trap_review(case_id, articles, buckets)
        difficulty = corpus_difficulty(record, notes_case)

        review["cases"][case_id] = {
            "borderline_review": {
                "status": "explicitly_marked_for_expert_review",
                "borderline_count": len(record["borderline"]),
                "article_ids": record["borderline"],
            },
            "raw_only_false_negative_review": raw_review,
            "rejected_candidate_false_negative_sample": rejected,
            "keyword_traps": traps,
            "same_company_or_theme_distractors_present": all(
                trap["bucket"] == "irrelevant" for trap in traps
            ),
            "corpus_difficulty": difficulty,
            "recommended_label_changes": [],
        }

        updated = dict(record)
        draft_status = record.get("draft_annotation_status", record.get("annotation_status"))
        if draft_status == "agent_qa_reviewed_expert_pending":
            draft_status = DRAFT_STATUS_BY_CASE[case_id]
        updated["draft_annotation_status"] = draft_status
        updated["annotation_status"] = "agent_qa_reviewed_expert_pending"
        updated["expert_review_status"] = "expert_review_pending"
        updated_golden.append(updated)

    too_easy_cases = [
        case_id
        for case_id, case in review["cases"].items()
        if case["corpus_difficulty"]["status"] == "revision_recommended"
    ]
    review["summary"]["too_easy_cases"] = too_easy_cases
    review["summary"]["potential_raw_only_false_negative_flags"] = sum(
        case["raw_only_false_negative_review"]["flag_count"]
        for case in review["cases"].values()
    )
    review["summary"]["rejected_sample_false_negatives_already_caught"] = sum(
        1
        for case in review["cases"].values()
        for item in case["rejected_candidate_false_negative_sample"]
        if item["qa_decision"] == "discovery_false_negative_already_caught_in_golden"
    )
    return updated_golden, review


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--golden-output",
        default="benchmark/datasets/request-article-retrieval/golden.jsonl",
        help="Path to write reviewed golden JSONL.",
    )
    parser.add_argument(
        "--review-output",
        default="benchmark/datasets/request-article-retrieval/agent_qa_review_notes.json",
        help="Path to write RD7 agent-side QA review notes.",
    )
    args = parser.parse_args()

    golden_output = Path(args.golden_output)
    review_output = Path(args.review_output)
    if not golden_output.is_absolute():
        golden_output = ROOT / golden_output
    if not review_output.is_absolute():
        review_output = ROOT / review_output

    updated_golden, review = build_review()
    golden_output.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in updated_golden),
        encoding="utf-8",
    )
    review_output.write_text(
        json.dumps(review, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"wrote {review_output.relative_to(ROOT)}; "
        f"expert_review_status={review['expert_review_status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
