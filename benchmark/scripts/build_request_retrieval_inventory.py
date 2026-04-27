#!/usr/bin/env python3
"""Build the request-driven retrieval candidate inventory.

The script intentionally uses only local state artifacts. It normalizes article
cards from markdown article files and raw collection JSON, deduplicates them by
normalized URL, and preserves all provenance values for later review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


ROOT = Path(__file__).resolve().parents[2]
ARTICLES_DIR = ROOT / ".state" / "articles"
RAW_DIR = ROOT / ".state" / "raw"

PROVENANCE_ORDER = [
    "article_md",
    "raw_collected_all",
    "raw_feb_collected",
    "raw_enriched",
]

TRACKING_PARAMS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
}

SOURCE_NAME_BY_ID = {
    "aimgroup": "AIM Group",
    "aim_group": "AIM Group",
    "costar": "CoStar",
    "costar_ir": "CoStar Group Investor Relations",
    "inman": "Inman",
    "mike_delprete": "Mike DelPrete",
    "mikedp_library": "Mike DelPrete Library",
    "onlinemarketplaces": "Online Marketplaces",
    "redfin": "Redfin",
    "zillow_newsroom": "Zillow Newsroom",
}


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


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return None
    if value.lower() in {"null", "none"}:
        return None
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [item.strip().strip('"').strip("'") for item in inner.split(",")]
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def parse_markdown_article(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    metadata: dict[str, Any] = {}
    body = text
    if text.startswith("---\n"):
        _, frontmatter, body = text.split("---\n", 2)
        for line in frontmatter.splitlines():
            if not line.strip() or ":" not in line:
                continue
            key, raw_value = line.split(":", 1)
            metadata[key.strip()] = parse_scalar(raw_value)

    body_lines = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            continue
        body_lines.append(stripped)

    body_text = "\n".join(body_lines)
    metadata["body_excerpt"] = compact_text(body_text)
    if not metadata.get("lead_or_summary"):
        metadata["lead_or_summary"] = compact_text(body_lines[0] if body_lines else None)
    return metadata


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower() or "https"
    netloc = parts.netloc.lower()
    if scheme == "http" and netloc.endswith(":80"):
        netloc = netloc[:-3]
    if scheme == "https" and netloc.endswith(":443"):
        netloc = netloc[:-4]

    query_pairs = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered.startswith("utm_") or lowered in TRACKING_PARAMS:
            continue
        query_pairs.append((key, value))

    path = parts.path.rstrip("/") or "/"
    query = urlencode(query_pairs, doseq=True)
    normalized = urlunsplit((scheme, netloc, path, query, ""))
    return normalized[:-1] if normalized.endswith("/") else normalized


def article_id_for_url(normalized_url: str) -> str:
    digest = hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()[:10]
    return f"art_{digest}"


def source_id_from_url(url: str | None) -> str | None:
    if not url:
        return None
    host = urlsplit(url).netloc.lower()
    host = host.removeprefix("www.")
    if "aimgroup.com" in host:
        return "aimgroup"
    if "inman.com" in host:
        return "inman"
    if "onlinemarketplaces.com" in host:
        return "onlinemarketplaces"
    if "zillow" in host:
        return "zillow_newsroom"
    if "redfin" in host:
        return "redfin"
    if "costargroup" in host or "costar" in host:
        return "costar_ir"
    if "mikedp.com" in host or "delprete" in host:
        return "mike_delprete"
    return host.split(".")[0] if host else None


def source_name_for(source_id: str | None, source_name: str | None = None) -> str | None:
    if source_name:
        return source_name
    if not source_id:
        return None
    return SOURCE_NAME_BY_ID.get(source_id, source_id)


def normalize_record(raw: dict[str, Any], provenance: str, artifact_ref: str) -> dict[str, Any] | None:
    url = raw.get("url")
    if not url:
        return None
    normalized_url = normalize_url(str(url))
    source_id = raw.get("source_id") or source_id_from_url(str(url))
    source_name = source_name_for(source_id, raw.get("source_name"))
    lead_or_summary = (
        raw.get("lead_or_summary")
        or raw.get("summary")
        or raw.get("raw_snippet")
        or raw.get("analyst_summary")
    )
    body_excerpt = raw.get("body_excerpt") or raw.get("raw_snippet") or raw.get("summary")

    return {
        "article_id": article_id_for_url(normalized_url),
        "normalized_url": normalized_url,
        "title": raw.get("title"),
        "source_id": source_id,
        "source_name": source_name,
        "published": raw.get("published"),
        "url": str(url),
        "lead_or_summary": compact_text(lead_or_summary),
        "body_excerpt": compact_text(body_excerpt),
        "provenance": [provenance],
        "artifact_refs": [artifact_ref],
        "analyst_summary": compact_text(raw.get("analyst_summary")),
        "why_it_matters": compact_text(raw.get("why_it_matters")),
        "avito_implication": compact_text(raw.get("avito_implication")),
        "topic_tags": raw.get("topic_tags"),
        "event_type": raw.get("event_type"),
        "priority_score": raw.get("priority_score"),
        "companies": raw.get("companies"),
    }


def merge_lists(existing: Any, incoming: Any) -> list[Any] | None:
    values: list[Any] = []
    for source in (existing, incoming):
        if not source:
            continue
        items = source if isinstance(source, list) else [source]
        for item in items:
            if item not in values:
                values.append(item)
    return values or None


def prefer_text(existing: Any, incoming: Any) -> Any:
    if not existing:
        return incoming
    if not incoming:
        return existing
    return incoming if len(str(incoming)) > len(str(existing)) else existing


def merge_candidate(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    for key in [
        "title",
        "source_id",
        "source_name",
        "published",
        "url",
        "event_type",
        "priority_score",
    ]:
        if existing.get(key) in (None, "", []):
            existing[key] = incoming.get(key)

    for key in [
        "lead_or_summary",
        "body_excerpt",
        "analyst_summary",
        "why_it_matters",
        "avito_implication",
    ]:
        existing[key] = prefer_text(existing.get(key), incoming.get(key))

    for key in ["provenance", "artifact_refs", "topic_tags", "companies"]:
        merged = merge_lists(existing.get(key), incoming.get(key))
        if merged is not None:
            existing[key] = merged

    existing["provenance"] = sorted(
        existing.get("provenance", []),
        key=lambda value: PROVENANCE_ORDER.index(value)
        if value in PROVENANCE_ORDER
        else len(PROVENANCE_ORDER),
    )
    return existing


def add_candidate(
    candidates_by_url: dict[str, dict[str, Any]],
    candidate: dict[str, Any] | None,
    stats: dict[str, int],
) -> None:
    if candidate is None:
        stats["missing_url_records"] += 1
        return
    normalized_url = candidate["normalized_url"]
    if normalized_url in candidates_by_url:
        stats["duplicates_merged"] += 1
        merge_candidate(candidates_by_url[normalized_url], candidate)
    else:
        candidates_by_url[normalized_url] = candidate


def iter_markdown_records() -> list[tuple[dict[str, Any], str]]:
    records = []
    for path in sorted(ARTICLES_DIR.glob("*/*.md")):
        article = parse_markdown_article(path)
        records.append((article, str(path.relative_to(ROOT))))
    return records


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_inventory() -> dict[str, Any]:
    candidates_by_url: dict[str, dict[str, Any]] = {}
    stats = {
        "article_md_records": 0,
        "raw_collected_all_records": 0,
        "raw_feb_collected_records": 0,
        "raw_enriched_records": 0,
        "nested_raw_children_with_inherited_source": 0,
        "duplicates_merged": 0,
        "missing_url_records": 0,
    }

    for record, artifact_ref in iter_markdown_records():
        stats["article_md_records"] += 1
        candidate = normalize_record(record, "article_md", artifact_ref)
        add_candidate(candidates_by_url, candidate, stats)

    nested_files = [
        ("collected-all.json", "raw_collected_all", "raw_collected_all_records"),
        ("feb-collected.json", "raw_feb_collected", "raw_feb_collected_records"),
    ]
    for filename, provenance, count_key in nested_files:
        data = read_json(RAW_DIR / filename)
        for source_group in data.get("items", []):
            parent_source_id = source_group.get("source_id")
            parent_source_name = source_group.get("source_name")
            for index, item in enumerate(source_group.get("items", [])):
                stats[count_key] += 1
                raw_item = dict(item)
                inherited = False
                if not raw_item.get("source_id") and parent_source_id:
                    raw_item["source_id"] = parent_source_id
                    inherited = True
                if not raw_item.get("source_name") and parent_source_name:
                    raw_item["source_name"] = parent_source_name
                    inherited = True
                if inherited:
                    stats["nested_raw_children_with_inherited_source"] += 1
                artifact_ref = f".state/raw/{filename}#{parent_source_id or 'unknown'}[{index}]"
                candidate = normalize_record(raw_item, provenance, artifact_ref)
                add_candidate(candidates_by_url, candidate, stats)

    enriched = read_json(RAW_DIR / "enriched-march-april.json")
    for index, item in enumerate(enriched.get("items", [])):
        stats["raw_enriched_records"] += 1
        artifact_ref = f".state/raw/enriched-march-april.json[{index}]"
        candidate = normalize_record(item, "raw_enriched", artifact_ref)
        add_candidate(candidates_by_url, candidate, stats)

    candidates = sorted(
        candidates_by_url.values(),
        key=lambda item: (
            item.get("published") or "",
            item.get("source_id") or "",
            item.get("title") or "",
            item["normalized_url"],
        ),
    )

    provenance_counts = {
        provenance: sum(1 for item in candidates if provenance in item.get("provenance", []))
        for provenance in PROVENANCE_ORDER
    }
    raw_only_count = sum(
        1
        for item in candidates
        if "article_md" not in item.get("provenance", [])
        and any(prov.startswith("raw_") for prov in item.get("provenance", []))
    )

    return {
        "schema_version": "candidate_inventory_v1",
        "benchmark_id": "request-article-retrieval",
        "source_files": [
            ".state/articles/*.md",
            ".state/raw/collected-all.json",
            ".state/raw/feb-collected.json",
            ".state/raw/enriched-march-april.json",
        ],
        "summary": {
            "input_record_counts": {
                "article_md": stats["article_md_records"],
                "raw_collected_all": stats["raw_collected_all_records"],
                "raw_feb_collected": stats["raw_feb_collected_records"],
                "raw_enriched": stats["raw_enriched_records"],
            },
            "unique_candidate_count": len(candidates),
            "provenance_counts": provenance_counts,
            "raw_only_candidate_count": raw_only_count,
            "duplicates_merged_count": stats["duplicates_merged"],
            "missing_url_record_count": stats["missing_url_records"],
            "nested_raw_children_with_inherited_source": stats[
                "nested_raw_children_with_inherited_source"
            ],
        },
        "candidates": candidates,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="benchmark/datasets/request-article-retrieval/candidate_inventory.json",
        help="Path to write the generated candidate inventory JSON.",
    )
    args = parser.parse_args()

    inventory = build_inventory()
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "wrote "
        f"{output_path.relative_to(ROOT)} "
        f"with {inventory['summary']['unique_candidate_count']} unique candidates "
        f"and {inventory['summary']['raw_only_candidate_count']} raw-only candidates"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
