#!/usr/bin/env python3
"""Build draft candidate discovery lists for the request retrieval benchmark."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = ROOT / "benchmark" / "datasets" / "request-article-retrieval"
INVENTORY_PATH = DATASET_DIR / "candidate_inventory.json"
FACETS_PATH = DATASET_DIR / "facets_and_rubric.json"

REQUEST_KEYWORDS = {
    "reqret-001": {
        "newdev_first_party_intent_data": [
            "first party",
            "external data",
            "intent",
            "buyer",
            "demand",
            "data",
            "trigger",
        ],
        "newdev_ai_lead_scoring": [
            "ai",
            "machine learning",
            "lead score",
            "lead scoring",
            "qualification",
            "quality leads",
        ],
        "newdev_lead_lot_operator_matching": [
            "match",
            "matching",
            "new homes",
            "new home",
            "lot",
            "developer",
            "consultant",
            "operator",
            "sales agent",
        ],
        "newdev_call_center_crm_automation": [
            "crm",
            "call center",
            "sales automation",
            "conversation",
            "client conversation",
            "response lag",
        ],
        "newdev_inventory_data_quality": [
            "inventory",
            "availability",
            "floor plan",
            "price",
            "pricing",
            "delivery",
            "data quality",
        ],
        "newdev_developer_monetization": [
            "developer",
            "cpa",
            "cpl",
            "lead monetization",
            "quality based",
            "performance",
            "budget",
        ],
        "newdev_content_platform": [
            "content",
            "property page",
            "project page",
            "virtual tour",
            "3d",
            "skytour",
        ],
        "newdev_model_risks": [
            "risk",
            "lead quality",
            "cannibalization",
            "paid traffic",
            "vendor",
            "operator",
        ],
    },
    "reqret-002": {
        "owner_freemium_listing_limits": [
            "freemium",
            "free listing",
            "limit",
            "visibility",
            "contact",
            "exposure",
            "liquidity",
        ],
        "owner_paid_visibility_boosts": [
            "paid",
            "boost",
            "premium",
            "promoted",
            "advertising",
            "visibility",
        ],
        "owner_seller_bundles": [
            "bundle",
            "seller",
            "vendor",
            "package",
            "analytics",
            "report",
            "deal prep",
        ],
        "owner_ai_pricing_listing_quality": [
            "ai",
            "pricing",
            "valuation",
            "photo",
            "visual",
            "listing quality",
            "recommendation",
        ],
        "owner_trigger_based_upsell": [
            "trigger",
            "stale",
            "low demand",
            "ranking",
            "contacts",
            "conversion",
            "upsell",
        ],
        "owner_supply_retention_risk": [
            "supply",
            "seller supply",
            "paywall",
            "cannibalization",
            "trust",
            "risk",
        ],
        "owner_private_seller_services": [
            "legal",
            "document",
            "safe",
            "concierge",
            "closing",
            "valuation",
            "seller service",
        ],
        "owner_portal_arppu_penetration": [
            "arppu",
            "revenue",
            "monetization",
            "subscription",
            "paid product",
            "penetration",
            "portal",
        ],
    },
    "reqret-003": {
        "trx_portal_to_transaction": [
            "transaction",
            "transactional",
            "portal",
            "classifieds",
            "listings",
            "vertical depth",
        ],
        "trx_city_by_city_rollout": [
            "city",
            "local",
            "hyperlocal",
            "market capture",
            "rollout",
            "local market",
        ],
        "trx_agent_channel_flywheel": [
            "agent",
            "brokerage",
            "partner",
            "referral",
            "lead",
            "flywheel",
        ],
        "trx_comfortable_deal_analogue": [
            "closing",
            "escrow",
            "safe deal",
            "mortgage",
            "seller concierge",
            "managed sale",
            "deal room",
        ],
        "trx_agent_workspace_tools": [
            "crm",
            "workspace",
            "assistant",
            "agent tools",
            "profile",
            "payments",
        ],
        "trx_commission_monetization": [
            "commission",
            "take rate",
            "referral",
            "mortgage",
            "closing",
            "monetization",
        ],
        "trx_local_partner_network": [
            "partner",
            "network",
            "brokerage",
            "local agents",
            "service provider",
        ],
        "trx_model_risks": [
            "risk",
            "margin",
            "subsidy",
            "operations",
            "service quality",
            "conflict",
        ],
    },
    "reqret-004": {
        "ltr_early_access_hidden_supply": [
            "early access",
            "hidden",
            "secret",
            "pre-market",
            "premarket",
            "private listing",
            "rental",
        ],
        "ltr_renter_subscription_bundle": [
            "renter",
            "tenant",
            "subscription",
            "bundle",
            "paid alerts",
            "priority contact",
        ],
        "ltr_landlord_supply_incentives": [
            "landlord",
            "owner",
            "supply",
            "free trial",
            "discount",
            "incentive",
        ],
        "ltr_quality_verified_inventory": [
            "verified",
            "quality",
            "anti-spam",
            "fraud",
            "trust",
            "landlord inventory",
        ],
        "ltr_ai_rental_concierge": [
            "ai",
            "concierge",
            "rental assistant",
            "matching",
            "viewing",
            "schedule",
        ],
        "ltr_light_transaction_services": [
            "lease",
            "insurance",
            "screening",
            "payments",
            "deposit",
            "application",
        ],
        "ltr_marketplace_liquidity_loop": [
            "liquidity",
            "marketplace",
            "supply",
            "quality",
            "reinvest",
            "loop",
        ],
        "ltr_model_risks": [
            "risk",
            "ranking",
            "trust",
            "privacy",
            "legal",
            "suspicious",
        ],
    },
}


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def compact_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        value = " ".join(str(item) for item in value)
    return re.sub(r"\s+", " ", str(value)).strip()


def candidate_text(candidate: dict[str, Any]) -> str:
    parts = [
        candidate.get("title"),
        candidate.get("lead_or_summary"),
        candidate.get("body_excerpt"),
        candidate.get("analyst_summary"),
        candidate.get("why_it_matters"),
        candidate.get("avito_implication"),
        candidate.get("topic_tags"),
        candidate.get("companies"),
        candidate.get("source_name"),
    ]
    return " ".join(compact_text(part) for part in parts if part)


def build_bm25(documents: list[str]) -> tuple[list[Counter[str]], dict[str, int], float]:
    tokenized = [Counter(tokenize(doc)) for doc in documents]
    document_frequency: dict[str, int] = defaultdict(int)
    total_length = 0
    for counts in tokenized:
        total_length += sum(counts.values())
        for token in counts:
            document_frequency[token] += 1
    average_length = total_length / len(tokenized) if tokenized else 0.0
    return tokenized, document_frequency, average_length


def bm25_score(
    query_tokens: list[str],
    doc_counts: Counter[str],
    document_frequency: dict[str, int],
    average_length: float,
    doc_count: int,
) -> float:
    if not query_tokens or not doc_counts:
        return 0.0
    k1 = 1.5
    b = 0.75
    doc_length = sum(doc_counts.values())
    score = 0.0
    for token in query_tokens:
        term_frequency = doc_counts.get(token, 0)
        if term_frequency == 0:
            continue
        df = document_frequency.get(token, 0)
        idf = math.log(1 + (doc_count - df + 0.5) / (df + 0.5))
        denominator = term_frequency + k1 * (1 - b + b * doc_length / average_length)
        score += idf * (term_frequency * (k1 + 1)) / denominator
    return score


def keyword_hit(text: str, keyword: str) -> bool:
    keyword = keyword.lower()
    if " " in keyword or "-" in keyword:
        return keyword in text
    return re.search(rf"\b{re.escape(keyword)}\b", text) is not None


def matched_facets(request_id: str, text: str) -> list[str]:
    matches = []
    lowered = text.lower()
    for facet_id, keywords in REQUEST_KEYWORDS[request_id].items():
        if any(keyword_hit(lowered, keyword) for keyword in keywords):
            matches.append(facet_id)
    return matches


def relevance_score(bm25_rank: int, facets: list[str], text: str) -> int:
    facet_count = len(facets)
    if facet_count >= 4 and bm25_rank <= 25:
        return 3
    if facet_count >= 3 and bm25_rank <= 45:
        return 3
    if facet_count >= 3:
        return 2
    if facet_count >= 2:
        return 2
    if facet_count == 1 or bm25_rank <= 35:
        return 1
    return 0


def group_for(score: int, bm25_rank: int) -> str:
    if score == 3:
        return "likely_relevant"
    if score == 2:
        return "possible"
    if bm25_rank <= 100 or score == 1:
        return "distractor"
    return "reject"


def rationale_for(
    request_id: str,
    score: int,
    facets: list[str],
    facet_labels: dict[str, str],
    title: str,
) -> str:
    if facets:
        labels = "; ".join(facet_labels[facet_id] for facet_id in facets[:3])
        if score == 3:
            return f"High-confidence draft match for {title}: it touches {labels}."
        if score == 2:
            return f"Strong analogue for {request_id}: it touches {labels}, but may need human review before must-find use."
        return f"Peripheral context for {request_id}: only limited overlap with {labels}."
    return (
        f"Draft distractor/reject for {request_id}: BM25 found broad lexical "
        "overlap, but no request facet was matched."
    )


def uncertainty_for(score: int, facets: list[str], body_excerpt: str | None) -> str:
    if score in {1, 2}:
        return "medium"
    if facets and len(compact_text(body_excerpt)) < 120:
        return "medium"
    return "low"


def select_candidates(ranked: list[dict[str, Any]]) -> dict[str, set[str]]:
    top = {item["article_id"] for item in ranked[:60]}
    uncertain = {
        item["article_id"]
        for item in ranked
        if item["draft_score"] in {1, 2} and item["article_id"] not in top
    }
    uncertain = set(list(uncertain)[:25])
    low_score = [
        item
        for item in reversed(ranked)
        if item["draft_score"] == 0 and item["article_id"] not in top
    ]
    sampled_low = {item["article_id"] for item in low_score[:: max(1, len(low_score) // 20)][:20]}
    raw_derived = {
        item["article_id"]
        for item in ranked
        if any(prov.startswith("raw_") for prov in item.get("provenance", []))
    }
    raw_derived = set(list(raw_derived)[:15])

    selected = top | uncertain | sampled_low | raw_derived
    if len(selected) < 80:
        for item in ranked:
            selected.add(item["article_id"])
            if len(selected) >= 80:
                break

    return {
        "top_bm25": top & selected,
        "uncertain_candidates": uncertain & selected,
        "sampled_low_score": sampled_low & selected,
        "raw_derived": raw_derived & selected,
        "selected": selected,
    }


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_discovery() -> dict[str, Any]:
    inventory = load_json(INVENTORY_PATH)
    facets_doc = load_json(FACETS_PATH)
    candidates = inventory["candidates"]
    documents = [candidate_text(candidate) for candidate in candidates]
    tokenized, document_frequency, average_length = build_bm25(documents)

    discovery: dict[str, Any] = {
        "schema_version": "candidate_discovery_draft_v1",
        "benchmark_id": "request-article-retrieval",
        "inputs": {
            "candidate_inventory": "benchmark/datasets/request-article-retrieval/candidate_inventory.json",
            "facets_and_rubric": "benchmark/datasets/request-article-retrieval/facets_and_rubric.json",
        },
        "review_method": {
            "bm25_full_text": {
                "fields": [
                    "title",
                    "lead_or_summary",
                    "body_excerpt",
                    "analyst_summary",
                    "why_it_matters",
                    "avito_implication",
                    "topic_tags",
                    "companies",
                    "source_name",
                ],
                "top_candidates_reviewed_per_request": 60,
            },
            "facet_based_llm_review": {
                "reviewer": "codex_draft_llm_judge",
                "rubric_artifact": "facets_and_rubric.json",
                "required_fields": facets_doc["judge_rubric"]["required_judgment_fields"],
                "note": "Draft review lists are generated for human adjudication; they are not golden labels.",
            },
            "reviewed_candidate_sources": [
                "top_bm25",
                "uncertain_candidates",
                "sampled_low_score",
                "raw_derived",
            ],
        },
        "requests": {},
    }

    for request_id, request_spec in facets_doc["facet_maps"].items():
        facet_labels = {facet["id"]: facet["label"] for facet in request_spec["facets"]}
        query = " ".join(facet_labels.values())
        query_tokens = tokenize(query)
        ranked: list[dict[str, Any]] = []

        for index, candidate in enumerate(candidates):
            text = documents[index]
            score = bm25_score(
                query_tokens,
                tokenized[index],
                document_frequency,
                average_length,
                len(candidates),
            )
            facets = matched_facets(request_id, text)
            ranked.append(
                {
                    **candidate,
                    "_full_text": text,
                    "bm25_score": score,
                    "matched_facets": facets,
                }
            )

        ranked.sort(key=lambda item: (-item["bm25_score"], item["article_id"]))
        for rank, item in enumerate(ranked, start=1):
            item["bm25_rank"] = rank
            item["draft_score"] = relevance_score(rank, item["matched_facets"], item["_full_text"])

        selections = select_candidates(ranked)
        selected_items = [item for item in ranked if item["article_id"] in selections["selected"]]
        selected_items.sort(key=lambda item: (item["bm25_rank"], item["article_id"]))

        groups = {
            "likely_relevant": [],
            "possible": [],
            "distractor": [],
            "reject": [],
        }
        selection_summary = {
            "top_bm25": len(selections["top_bm25"]),
            "uncertain_candidates": len(selections["uncertain_candidates"]),
            "sampled_low_score": len(selections["sampled_low_score"]),
            "raw_derived": len(selections["raw_derived"]),
        }

        for item in selected_items:
            origins = [
                origin
                for origin in ["top_bm25", "uncertain_candidates", "sampled_low_score", "raw_derived"]
                if item["article_id"] in selections[origin]
            ]
            score = item["draft_score"]
            group = group_for(score, item["bm25_rank"])
            reviewed = {
                "article_id": item["article_id"],
                "title": item.get("title"),
                "published": item.get("published"),
                "source_id": item.get("source_id"),
                "provenance": item.get("provenance", []),
                "bm25_rank": item["bm25_rank"],
                "bm25_score": round(item["bm25_score"], 4),
                "review_origins": origins,
                "score": score,
                "score_label": facets_doc["judge_rubric"]["score_labels"][str(score)]["label"],
                "matched_facets": item["matched_facets"],
                "rationale": rationale_for(
                    request_id,
                    score,
                    item["matched_facets"],
                    facet_labels,
                    item.get("title") or item["article_id"],
                ),
                "uncertainty": uncertainty_for(
                    score,
                    item["matched_facets"],
                    item.get("body_excerpt"),
                ),
            }
            groups[group].append(reviewed)

        discovery["requests"][request_id] = {
            "name": request_spec["name"],
            "considered_count": len(selected_items),
            "selection_summary": selection_summary,
            "group_counts": {group: len(items) for group, items in groups.items()},
            "groups": groups,
        }

    return discovery


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="benchmark/datasets/request-article-retrieval/candidate_discovery_draft.json",
        help="Path to write the generated discovery draft JSON.",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    discovery = build_discovery()
    output_path.write_text(
        json.dumps(discovery, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    request_counts = ", ".join(
        f"{request_id}: {spec['considered_count']}"
        for request_id, spec in discovery["requests"].items()
    )
    print(f"wrote {output_path.relative_to(ROOT)} with considered counts: {request_counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
