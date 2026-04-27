#!/usr/bin/env python3
"""Build draft golden labels for the request retrieval benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = ROOT / "benchmark" / "datasets" / "request-article-retrieval"
INPUTS_PATH = DATASET_DIR / "inputs.jsonl"

DRAFT_LABELS: dict[str, dict[str, Any]] = {
    "reqret-001": {
        "annotation_status": "draft_rd6a",
        "must_find": [
            "art_58952c33fa",
            "art_d97bc82afc",
            "art_82b95d2e44",
            "art_8f98e029e7",
            "art_23a5961b7e",
            "art_04e6e8dac8",
        ],
        "nice_to_have": [
            "art_5d20bf2093",
            "art_34f650f1cc",
            "art_708b7f8581",
            "art_bcc494b3d9",
            "art_6767fb98a1",
            "art_31a1d23146",
            "art_50fc90629f",
            "art_36aaa4c8a0",
            "art_f064d3ecb3",
        ],
        "borderline": [
            "art_45ed1d626f",
            "art_1a5306798b",
            "art_28cfe6472f",
            "art_59f7b278e8",
            "art_948b5c44ba",
            "art_4030ad1705",
            "art_81c458b262",
            "art_5b9f31d0b0",
            "art_c23664bcfd",
            "art_7ce811300b",
            "art_fad8fd2850",
        ],
        "critical_miss_ids": [
            "art_58952c33fa",
            "art_d97bc82afc",
            "art_82b95d2e44",
        ],
        "rationale": {
            "art_58952c33fa": "Direct new-homes AI sales-agent signal for buyer qualification and lead handling.",
            "art_d97bc82afc": "Directly supports the data-moat part of the hypothesis: data quality, not generic AI, decides property search advantage.",
            "art_82b95d2e44": "Direct evidence that response-time and CRM automation can improve lead conversion in real estate workflows.",
            "art_8f98e029e7": "Shows client-conversation capture turning CRM interactions into structured data, relevant to CDP and intent modeling.",
            "art_23a5961b7e": "Evidence that AI changes buyer search behavior, useful for buyer intent and recommendation hypotheses.",
            "art_04e6e8dac8": "Portal case emphasizing data quality, agent tools, and UX refinement rather than generic AI hype.",
        },
    },
    "reqret-002": {
        "annotation_status": "draft_rd6a",
        "must_find": [
            "art_426e4d1d66",
            "art_bbd29db3ea",
            "art_0dea901dc1",
            "art_457eb7d57f",
        ],
        "nice_to_have": [
            "art_1efeebcc37",
            "art_df3527fb92",
            "art_8ddecd35bd",
            "art_c9bc8f2830",
            "art_18162cc3a6",
            "art_708b7f8581",
            "art_34f650f1cc",
            "art_36aaa4c8a0",
        ],
        "borderline": [
            "art_50fc90629f",
            "art_6791c53b69",
            "art_f0e770ca4c",
            "art_6b35e50918",
            "art_230252f03d",
            "art_5f88c9e5af",
            "art_a041604fe0",
            "art_0269b4b80c",
            "art_6e8c47d4a6",
            "art_2bccef547b",
        ],
        "critical_miss_ids": [
            "art_426e4d1d66",
            "art_0dea901dc1",
            "art_457eb7d57f",
        ],
        "rationale": {
            "art_426e4d1d66": "Direct vendor-paid portal advertising case for monetizing sellers without a blanket paid-listing shift.",
            "art_bbd29db3ea": "Alternate/local duplicate of the Daft vendor-paid case; still direct evidence for seller-paid portal advertising.",
            "art_0dea901dc1": "Hemnet ARPA pressure is direct evidence for portal seller monetization upside and risk.",
            "art_457eb7d57f": "Direct seller-service monetization analogue: a paid/financed service around the selling process rather than basic listing fees.",
        },
    },
    "reqret-003": {
        "annotation_status": "draft_rd6b",
        "must_find": [
            "art_2bccef547b",
            "art_aab9520bd2",
            "art_60d8b8e94d",
            "art_ac8e31707e",
            "art_7cedc9f5d1",
            "art_7b08997fd3",
        ],
        "nice_to_have": [
            "art_43ca52b1b8",
            "art_905093b4eb",
            "art_5d20bf2093",
            "art_6b35e50918",
            "art_300e7d1767",
            "art_18162cc3a6",
            "art_3d7bcc13cf",
            "art_8f98e029e7",
            "art_457eb7d57f",
        ],
        "borderline": [
            "art_34f650f1cc",
            "art_230252f03d",
            "art_8cbd363e7e",
            "art_471dc4626e",
            "art_45ed1d626f",
            "art_24feda3c9d",
            "art_4030ad1705",
            "art_3ec9c9bdb8",
            "art_f6c8f32cd9",
            "art_b3077b5a5a",
        ],
        "critical_miss_ids": [
            "art_2bccef547b",
            "art_aab9520bd2",
            "art_60d8b8e94d",
        ],
        "rationale": {
            "art_2bccef547b": "Direct classifieds-to-property-transactions case in MENA, closely matching the RRE TRX expansion hypothesis.",
            "art_aab9520bd2": "Direct evidence of adding closing and escrow tooling to an end-to-end residential transaction stack.",
            "art_60d8b8e94d": "Direct portal-to-transaction expansion case for Southeast Asia, relevant to classifieds moving beyond listings.",
            "art_ac8e31707e": "Direct mortgage capability signal for transaction-service bundling around residential deals.",
            "art_7cedc9f5d1": "Closing-management expansion shows a transaction workflow layer adjacent to safe deal and operational automation.",
            "art_7b08997fd3": "Strong horizontal-classifieds-to-vertical-depth analogue with services and transactions layered on top of listings.",
        },
    },
    "reqret-004": {
        "annotation_status": "draft_rd6b",
        "must_find": [
            "art_6b7b3fd7b1",
            "art_952009b665",
            "art_1efeebcc37",
            "art_d967e3af68",
            "art_3e66bc3b7a",
            "art_5b9f31d0b0",
        ],
        "nice_to_have": [
            "art_934aa5a19a",
            "art_353de0c413",
            "art_d23a9ccbdb",
            "art_04e6e8dac8",
            "art_c9bc8f2830",
            "art_d97bc82afc",
            "art_7cedc9f5d1",
            "art_06e2473ec3",
        ],
        "borderline": [
            "art_5f529eefc3",
            "art_be09dabda5",
            "art_eb620165d4",
            "art_2b8a48ec58",
            "art_5593175d64",
            "art_18162cc3a6",
            "art_50fc90629f",
            "art_8ddecd35bd",
            "art_0dea901dc1",
            "art_3d7bcc13cf",
            "art_9a9b4c62d3",
        ],
        "critical_miss_ids": [
            "art_6b7b3fd7b1",
            "art_952009b665",
            "art_1efeebcc37",
        ],
        "rationale": {
            "art_6b7b3fd7b1": "Direct rental workflow signal: AI transformation of the rental application process maps to Rent Plus service value.",
            "art_952009b665": "Direct landlord-supply analogue around shifting sellers into rental supply, relevant to the supply loop.",
            "art_1efeebcc37": "Consumer subscription revenue diversification is a direct analogue for paid renter or buyer access bundles.",
            "art_d967e3af68": "BoligPortal digital services performance is a direct rental marketplace monetization and services signal.",
            "art_3e66bc3b7a": "Rent.com.au milestone gives a rental marketplace monetization benchmark and operating signal.",
            "art_5b9f31d0b0": "Renter-facing AI mode is directly relevant to paid rental search, matching, and decision support.",
        },
    },
}


def read_inputs() -> dict[str, dict[str, Any]]:
    cases = {}
    for line in INPUTS_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        cases[item["id"]] = item
    return cases


def bucket_conflicts(record: dict[str, Any]) -> set[str]:
    seen: dict[str, str] = {}
    conflicts = set()
    for bucket in ["must_find", "nice_to_have", "borderline", "irrelevant"]:
        for article_id in record[bucket]:
            if article_id in seen:
                conflicts.add(article_id)
            seen[article_id] = bucket
    return conflicts


def build_golden() -> list[dict[str, Any]]:
    inputs = read_inputs()
    records = []
    for case_id, labels in DRAFT_LABELS.items():
        corpus_ids = [article["article_id"] for article in inputs[case_id]["corpus"]]
        labeled_ids = set(labels["must_find"]) | set(labels["nice_to_have"]) | set(labels["borderline"])
        irrelevant = [article_id for article_id in corpus_ids if article_id not in labeled_ids]
        record = {
            "id": case_id,
            "annotation_status": labels["annotation_status"],
            "must_find": labels["must_find"],
            "nice_to_have": labels["nice_to_have"],
            "borderline": labels["borderline"],
            "irrelevant": irrelevant,
            "critical_miss_ids": labels["critical_miss_ids"],
            "rationale": labels["rationale"],
        }
        conflicts = bucket_conflicts(record)
        if conflicts:
            raise ValueError(f"{case_id} has bucket conflicts: {sorted(conflicts)}")
        unknown = set(record["must_find"] + record["nice_to_have"] + record["borderline"] + record["irrelevant"]) - set(corpus_ids)
        if unknown:
            raise ValueError(f"{case_id} labels unknown article ids: {sorted(unknown)}")
        if not set(record["critical_miss_ids"]) <= set(record["must_find"]):
            raise ValueError(f"{case_id} critical miss ids must be a subset of must_find")
        missing_rationale = set(record["must_find"]) - set(record["rationale"])
        if missing_rationale:
            raise ValueError(f"{case_id} missing rationale for {sorted(missing_rationale)}")
        records.append(record)
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="benchmark/datasets/request-article-retrieval/golden.jsonl",
        help="Path to write draft golden JSONL.",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    records = build_golden()
    output_path.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    print(f"wrote {output_path.relative_to(ROOT)} with {len(records)} draft records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
