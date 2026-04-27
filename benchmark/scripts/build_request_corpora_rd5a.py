#!/usr/bin/env python3
"""Build draft corpora for the request retrieval benchmark."""

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

DEFAULT_CASES = ["reqret-001", "reqret-002", "reqret-003", "reqret-004"]
TARGET_CORPUS_SIZE = 50
MIN_DISTRACTOR_RATIO = 0.30
LOCAL_NML_PREFIX_RE = re.compile(r"^Local NML (?:analogue|text) \([^)]*\): ")

BODY_EXCERPT_OVERRIDES = {
    "art_5d20bf2093": (
        "Local NML analogue (.state/raw/nml_2025.md:6338, Plus Group creates "
        "AI bot for Cian, Avito and DomClick real estate portals): Plus Group "
        "launched an AI bot for realtor chats on major Russian real estate "
        "portals. It responds 24/7, collects budget, space, location and "
        "contacts, creates a CRM client profile, escalates to a contact center "
        "when needed, and is positioned as a way to prevent lost chats and "
        "improve lead conversion without extra ad spend or staffing."
    ),
    "art_bcc494b3d9": (
        "Local NML analogue (.state/raw/nml.md:1780, Property sites race to "
        "replace filters: Finn launches hybrid chat-and-map tool): Finn is "
        "piloting AI-first home search with a conversational interface, "
        "interactive map and live property previews. The product uses "
        "natural-language understanding to surface buyer intent, asks follow-up "
        "questions, uses proprietary listing, pricing and behavioral data, and "
        "is framed as a shift from filter-based search to personalized "
        "discovery."
    ),
    "art_23a5961b7e": (
        "Zillow, Redfin and Zumper all moved home search into AI-driven "
        "conversational interfaces, showing that buyers and renters are "
        "starting to search through natural-language prompts rather than only "
        "through filters. Related coverage describes Zillow's ChatGPT app, "
        "Zillow's earlier natural-language search work, Redfin's ChatGPT home "
        "search launch, and Zumper survey data showing renter use of AI tools "
        "more than doubled year over year."
    ),
    "art_471dc4626e": (
        "Local NML analogue (.state/raw/nml_2025.md:1830, Zillow rolling back "
        "NAR listing preference): Zillow began rolling back a policy that "
        "separated NAR-member listings from FSBO, auction and other non-NAR "
        "inventory. The change responds to MLS policy shifts and the broader "
        "legal and industry debate over listing display, consumer access, NAR "
        "rules and portal control after earlier litigation involving Zillow, "
        "NAR and REX."
    ),
    "art_6b7b3fd7b1": (
        "Local NML analogue (.state/raw/nml_2025.md:5227, ImmoScout24 launches "
        "AI assistant HeyImmo): ImmoScout24 launched HeyImmo, an AI assistant "
        "for owners, tenants, buyers and renters. It gives personalized "
        "property recommendations, helps assess market prices and financing, "
        "supports tenants with utility bills and rent-increase questions, and "
        "helps owners and landlords with value improvement and market context."
    ),
    "art_8ddecd35bd": (
        "Local NML analogue (.state/raw/nml_2025.md:465, Compass to launch "
        "private-listing property marketplace): Compass planned a client-facing "
        "marketplace for exclusive listings unavailable on public portals. The "
        "product supports seller clients who want private marketing before MLS "
        "exposure and gives Compass-represented buyers access to inventory they "
        "cannot find on Zillow, Realtor.com or other portals, reinforcing "
        "Compass's private-listing strategy."
    ),
    "art_0269b4b80c": (
        "Local NML analogue (.state/raw/nml.md:1780, Property sites race to "
        "replace filters: Finn launches hybrid chat-and-map tool): Finn's AI "
        "search pilot shows how portals are moving toward conversational "
        "discovery rather than static filters. The system combines chat, map "
        "and property previews, asks proactive questions about budget and "
        "property type, and uses marketplace data to infer deeper buyer intent "
        "and create more relevant search results."
    ),
    "art_daf0b0d0d9": (
        "Local NML analogue (.state/raw/nml.md:636, Compass fails to get "
        "injunction against Zillow ban): A federal judge rejected Compass's "
        "request for an injunction against Zillow's policy banning listings "
        "that were privately marketed before public portal exposure. The case "
        "is a close analogue to Compass/NWMLS private-listing conflict because "
        "it centers on pocket listings, portal access rules, seller choice and "
        "competition between brokerage inventory strategies and open-market "
        "policies."
    ),
    "art_04e6e8dac8": (
        "Local NML analogue (.state/raw/nml.md:491, Property Finder raises "
        "$170M investment; .state/raw/nml.md:1305, Property Finder verification "
        "system): Property Finder raised new capital after earlier equity and "
        "debt funding, citing product scale, market position and products such "
        "as credit optimizer, home valuation and super agent. A separate NML "
        "item describes its shift toward prevention-first listing quality using "
        "official Dubai Land Department APIs and AI verification to reduce fake "
        "or inconsistent listings."
    ),
    "art_1b810e53b7": (
        "Local NML analogue (.state/raw/nml_2025.md:4902, Kleinanzeigen rolls "
        "out new offers for real estate professionals; .state/raw/nml_2025.md:"
        "6516, Bayut TruBroker): Related examples show portals competing on "
        "real estate professional relationships through project pages for new "
        "construction, richer listing formats, mortgage calculators and "
        "agent-quality badges that reward responsiveness and listing accuracy. "
        "This is a close analogue to differentiating against horizontal "
        "classifieds through verified supply and agent trust."
    ),
    "art_2bccef547b": (
        "Local NML analogue (.state/raw/nml_2025.md:6010, Dubizzle and Bayut "
        "sign MoU with Prypco; .state/raw/nml_2025.md:4911, Dubizzle Group IPO): "
        "Dubizzle and Bayut signed a partnership with Prypco to provide online "
        "mortgage access and repayment estimates to property users. NML also "
        "describes Dubizzle Group as a UAE classifieds operator and Bayut parent "
        "with real estate, automotive and general marketplaces, using scale and "
        "adjacent services to deepen property transactions beyond listings."
    ),
    "art_3d7bcc13cf": (
        "Local NML analogue (.state/raw/nml.md:150, Zillow played nice before "
        "going nuclear against private listings; .state/raw/nml_2025.md:6093, "
        "QuintoAndar tools for agents): NML examples show agent-ecosystem "
        "competition moving beyond listings into recruitment, retention and "
        "workflow. Zillow considered brokerage perks and CRM discounts to align "
        "agents against private-listing networks, while QuintoAndar shares "
        "search profiles and curated portfolio tools with agents to help them "
        "acquire and retain clients."
    ),
    "art_3ec9c9bdb8": (
        "Local NML analogue (.state/raw/nml.md:181, Wildberries expands car and "
        "real estate sales; .state/raw/nml.md:1089, Kaspi marketplace and "
        "classifieds revenue): Wildberries extended its e-commerce marketplace "
        "into cars and new-build apartments, growing developer inventory and "
        "adding direct contact mechanics. Kaspi shows the broader marketplace "
        "pattern of combining e-commerce, advertising and classifieds, including "
        "auto and real estate verticals, as adjacent revenue engines."
    ),
    "art_60d8b8e94d": (
        "Local NML analogue (.state/raw/nml_2025.md:5605, Lifull Connect: Taking "
        "on PropertyGuru, 99 Group with new SE Asian division): Lifull Connect "
        "acquired DCG property assets, launched SEA Connect Ventures and framed "
        "the next strategic step as building a full-stack marketplace that "
        "combines classifieds, transactions and partner networks. The article "
        "also notes the challenge of generating sustainable revenue in Southeast "
        "Asian property portals where listing-fee models are weaker."
    ),
    "art_6dd0cbd6be": (
        "Local NML analogue (.state/raw/nml.md:40, Avito Real Estate opens "
        "property location maps to advertisers): Avito Real Estate opened map "
        "placements to advertisers, giving brands native visibility inside "
        "property search without distracting from listings. The product targets "
        "a high-income real estate audience and lets advertisers route users to "
        "more detailed commercial information, showing Avito expanding richer "
        "paid ad formats beyond standard listings."
    ),
    "art_7b08997fd3": (
        "Local NML analogue (.state/raw/nml_2025.md:4029, Frontier Digital "
        "Ventures marketplace portfolio; .state/raw/nml_2025.md:5605, Lifull "
        "Connect SEA division): NML examples describe horizontal or portfolio "
        "marketplace operators deepening selected verticals through property "
        "brands, acquisitions and partner networks. Lifull Connect's Southeast "
        "Asia plan explicitly targets a full-stack property marketplace that "
        "adds transactions and partner services on top of classifieds."
    ),
    "art_aab9520bd2": (
        "Local NML text (.state/raw/nml.md:1714, Opendoor acquires Doma's "
        "closing, escrow tools): Opendoor acquired Doma's closing and escrow "
        "operations, subject to regulatory approval, to make closing faster, "
        "cheaper and more certain. The deal is positioned as a step toward "
        "Opendoor becoming closing infrastructure for U.S. real estate, with "
        "Doma's data, algorithms and closing professionals supporting title "
        "acceptance and refinance workflows."
    ),
    "art_df3527fb92": (
        "Local NML analogue (.state/raw/nml.md:40, Avito Real Estate opens "
        "property location maps to advertisers; .state/raw/nml_2025.md:3288, "
        "postview analytics): Avito Real Estate's map ad product lets brands "
        "reach property users through native placements and advertiser landing "
        "links. A separate NML item explains postview analytics, which measures "
        "how ad impressions influence later user behavior, making the combined "
        "analogue relevant to Avito AdTech analytics and seller performance "
        "measurement."
    ),
    "art_f6c8f32cd9": (
        "Local NML analogue (.state/raw/nml.md:29, Kolesa Group spends $1.4M "
        "to clean up auto and real estate listings; .state/raw/nml_2025.md:"
        "3614, Kolesa Group 2024): Kolesa Group operates automotive and real "
        "estate classifieds and invested heavily in cleaning up fraudulent "
        "listings, suspicious accounts, fake photos and spam. NML also reports "
        "Kolesa's auto marketplace scale and dealer monetization, making it a "
        "useful analogue for monetizing and protecting high-value classifieds "
        "verticals."
    ),
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_request_text(case_id: str) -> str:
    plan = PLAN_PATH.read_text(encoding="utf-8")
    pattern = rf"### {re.escape(case_id)}[^\n]*\n\n(?P<body>.*?)(?=\n### reqret-|\n## Dataset Contract)"
    match = re.search(pattern, plan, flags=re.S)
    if not match:
        raise ValueError(f"request seed not found for {case_id}")
    return match.group("body").strip()


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def model_facing_excerpt(candidate: dict[str, Any]) -> str | None:
    excerpt = BODY_EXCERPT_OVERRIDES.get(candidate["article_id"], candidate.get("body_excerpt"))
    if not isinstance(excerpt, str):
        return excerpt
    return LOCAL_NML_PREFIX_RE.sub("", excerpt)


def candidate_card(candidate: dict[str, Any]) -> dict[str, Any]:
    card = {
        "article_id": candidate["article_id"],
        "body_excerpt": model_facing_excerpt(candidate),
        "normalized_url": candidate["normalized_url"],
        "published": candidate.get("published"),
        "title": candidate.get("title"),
    }
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
        help="Case id to include. Repeat for multiple cases. Defaults to all request-retrieval cases.",
    )
    parser.add_argument(
        "--milestone",
        default="RD5b",
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
        f"{display_path(inputs_path)} and {display_path(notes_path)} "
        f"for {', '.join(case_ids)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
