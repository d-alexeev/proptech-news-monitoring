#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import datetime, timezone
from typing import Any

import russian_text_gate


BODY_STATUS_VALUES = {"full", "snippet_fallback", "paywall_stub"}
SOURCE_QUALITY_VALUES = {
    "primary_source",
    "industry_analysis",
    "expert_analysis",
    "trade_media",
    "behavioral_signal",
    "mobile_store",
    "manual_blocked",
}
FORBIDDEN_DIGEST_MARKERS = [
    ".state/",
    ".state/articles/",
    "article_file",
    "__20",
    "operator notes",
    "run id",
]
RUSSIAN_DELIVERY_PROFILES = {"telegram_digest", "telegram_weekly_digest"}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_json(path: pathlib.Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: pathlib.Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: pathlib.Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")


def rel(path: pathlib.Path, repo_root: pathlib.Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def run_timestamp(run_id: str) -> str:
    return run_id.split("-", 1)[0]


def coerce_items(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("items", "shortlisted_items", "shortlist", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    raise ValueError("expected JSON array or object containing an item list")


def url_keys(item: dict) -> set[str]:
    return {
        str(value).rstrip("/")
        for value in (item.get("url"), item.get("canonical_url"))
        if value
    }


def load_shortlisted_urls(shortlist_path: pathlib.Path) -> set[str]:
    items = [
        item
        for item in coerce_items(read_json(shortlist_path))
        if item.get("triage_decision") == "shortlist"
    ]
    urls: set[str] = set()
    for item in items:
        urls.update(url_keys(item))
    return urls


def load_prefetch_by_url(article_prefetch_result_path: pathlib.Path) -> dict[str, dict]:
    payload = read_json(article_prefetch_result_path)
    results = coerce_items(payload.get("results", []) if isinstance(payload, dict) else payload)
    by_url: dict[str, dict] = {}
    for item in results:
        for key in url_keys(item):
            by_url[key] = item
    return by_url


def require_keys(name: str, item: dict, keys: list[str]) -> None:
    missing = [key for key in keys if key not in item]
    if missing:
        raise ValueError(f"{name} missing required fields: {', '.join(missing)}")


def validate_digest_markdown(markdown: str) -> None:
    lowered = markdown.lower()
    for marker in FORBIDDEN_DIGEST_MARKERS:
        if marker.lower() in lowered:
            raise ValueError(f"digest markdown contains forbidden runtime marker: {marker}")


def validate_russian_delivery_text(draft: dict, delivery_profile: str) -> None:
    if delivery_profile not in RUSSIAN_DELIVERY_PROFILES:
        return
    russian_text_gate.require_russian_text(str(draft.get("digest_markdown", "")), field_path="digest_markdown")
    for index, item in enumerate(draft.get("enriched_items", [])):
        for key in ("analyst_summary", "why_it_matters", "avito_implication"):
            russian_text_gate.require_russian_text(str(item.get(key, "")), field_path=f"enriched_items[{index}].{key}")
        for evidence_index, evidence in enumerate(item.get("evidence_points", [])):
            russian_text_gate.require_russian_text(
                str(evidence),
                field_path=f"enriched_items[{index}].evidence_points[{evidence_index}]",
            )
    daily = draft.get("daily_brief", {})
    for index, note in enumerate(daily.get("selection_notes", [])):
        russian_text_gate.require_russian_text(str(note), field_path=f"daily_brief.selection_notes[{index}]")
    for index, card in enumerate(daily.get("story_cards", [])):
        for key in ("analyst_summary", "why_it_matters", "avito_implication"):
            russian_text_gate.require_russian_text(str(card.get(key, "")), field_path=f"daily_brief.story_cards[{index}].{key}")
        for evidence_index, evidence in enumerate(card.get("evidence_notes", [])):
            russian_text_gate.require_russian_text(
                str(evidence),
                field_path=f"daily_brief.story_cards[{index}].evidence_notes[{evidence_index}]",
            )
    qa_review = draft.get("qa_review", {})
    if isinstance(qa_review, dict) and qa_review.get("summary"):
        russian_text_gate.require_russian_text(str(qa_review.get("summary", "")), field_path="qa_review.summary")


def validate_enriched_items(enriched_items: list[dict], shortlisted_urls: set[str], prefetch_by_url: dict[str, dict]) -> None:
    required = [
        "source_id",
        "url",
        "canonical_url",
        "title",
        "published",
        "companies",
        "regions",
        "topic_tags",
        "event_type",
        "priority_score",
        "confidence",
        "analyst_summary",
        "why_it_matters",
        "avito_implication",
        "story_id",
        "body_status",
        "article_file",
        "evidence_points",
        "source_quality",
    ]
    for index, item in enumerate(enriched_items):
        require_keys(f"enriched_items[{index}]", item, required)
        item_urls = url_keys(item)
        if not item_urls.intersection(shortlisted_urls):
            raise ValueError(f"enriched item url not in current-run shortlist: {item.get('url')}")
        if item["body_status"] not in BODY_STATUS_VALUES:
            raise ValueError(f"invalid body_status for {item.get('url')}: {item['body_status']}")
        if item["source_quality"] not in SOURCE_QUALITY_VALUES:
            raise ValueError(f"invalid source_quality for {item.get('url')}: {item['source_quality']}")
        if not isinstance(item["priority_score"], int) or not 0 <= item["priority_score"] <= 100:
            raise ValueError(f"priority_score must be integer 0..100 for {item.get('url')}")
        if not isinstance(item["confidence"], (int, float)) or not 0 <= float(item["confidence"]) <= 1:
            raise ValueError(f"confidence must be numeric 0..1 for {item.get('url')}")
        matched_prefetch = next((prefetch_by_url[key] for key in item_urls if key in prefetch_by_url), None)
        if matched_prefetch is None:
            raise ValueError(f"enriched item missing article prefetch match: {item.get('url')}")
        if item["body_status"] == "full":
            if matched_prefetch.get("body_status_hint") != "full":
                raise ValueError(f"full body_status without matching full prefetch entry: {item.get('url')}")
            if not item.get("article_file"):
                raise ValueError(f"full body_status requires article_file: {item.get('url')}")
        if item["body_status"] == "paywall_stub" and item.get("evidence_points"):
            raise ValueError(f"paywall_stub must not contain evidence_points: {item.get('url')}")


def validate_draft(
    draft: dict,
    run_id: str,
    run_date: str,
    source_group: str,
    delivery_profile: str,
    shortlisted_urls: set[str],
    prefetch_by_url: dict[str, dict],
) -> None:
    require_keys(
        "finish draft",
        draft,
        [
            "schema_version",
            "run_id",
            "run_date",
            "source_group",
            "delivery_profile",
            "enriched_items",
            "daily_brief",
            "digest_markdown",
            "qa_review",
            "telegram_delivery",
        ],
    )
    if draft["schema_version"] != 1:
        raise ValueError("finish draft schema_version must be 1")
    if draft["run_id"] != run_id:
        raise ValueError("finish draft run_id does not match wrapper run_id")
    if draft["run_date"] != run_date:
        raise ValueError("finish draft run_date does not match wrapper run_date")
    if draft["source_group"] != source_group:
        raise ValueError("finish draft source_group does not match wrapper source_group")
    if draft["delivery_profile"] != delivery_profile:
        raise ValueError("finish draft delivery_profile does not match wrapper delivery_profile")
    if not isinstance(draft["enriched_items"], list) or not draft["enriched_items"]:
        raise ValueError("finish draft enriched_items must be a non-empty list")
    validate_enriched_items(draft["enriched_items"], shortlisted_urls, prefetch_by_url)
    if not isinstance(draft["daily_brief"], dict):
        raise ValueError("finish draft daily_brief must be an object")
    validate_digest_markdown(str(draft["digest_markdown"]))
    validate_russian_delivery_text(draft, delivery_profile)
    qa_review = draft["qa_review"]
    if not isinstance(qa_review, dict):
        raise ValueError("finish draft qa_review must be an object")
    if qa_review.get("status") not in {"validated", "warnings"}:
        raise ValueError("qa_review.status must be validated or warnings for production-ready Stage C")
    if int(qa_review.get("critical_findings_count", 1)) != 0:
        raise ValueError("qa_review.critical_findings_count must be 0 for production-ready Stage C")


def evidence_completeness(enriched_items: list[dict]) -> str:
    statuses = {item.get("body_status") for item in enriched_items}
    if statuses == {"snippet_fallback"}:
        return "all_snippet_fallback"
    if "full" in statuses:
        return "mixed_or_full_evidence"
    return "partial_non_full_evidence"


def build_scrape_manifest(
    run_id: str,
    run_date: str,
    source_group: str,
    enriched_path: str,
    article_prefetch_result: str,
    enriched_items: list[dict],
    warnings: list[str],
) -> dict:
    timestamp = run_timestamp(run_id)
    full_run_id = f"scrape_and_enrich__{timestamp}__{source_group}"
    completeness = evidence_completeness(enriched_items)
    return {
        "run_id": full_run_id,
        "mode": "scrape_and_enrich",
        "started_at": now_iso(),
        "finished_at": now_iso(),
        "status": "completed",
        "inputs": [article_prefetch_result],
        "outputs": [enriched_path],
        "source_groups": [source_group],
        "counts": {
            "enriched_count": len(enriched_items),
            "full_count": sum(1 for item in enriched_items if item.get("body_status") == "full"),
            "snippet_fallback_count": sum(1 for item in enriched_items if item.get("body_status") == "snippet_fallback"),
            "paywall_stub_count": sum(1 for item in enriched_items if item.get("body_status") == "paywall_stub"),
        },
        "warnings": warnings,
        "errors": [],
        "operator_report": {
            "enrichment": {
                "status": "completed",
                "evidence_completeness": completeness,
            }
        },
        "notes": [f"Materialized by stage_c_finish for {run_date}."],
    }


def build_daily_brief(draft: dict, run_id: str, run_date: str, delivery_profile: str, markdown_path: str) -> dict:
    daily = dict(draft["daily_brief"])
    story_ids = [item["story_id"] for item in draft["enriched_items"]]
    daily.update({
        "brief_id": f"{run_date}__{delivery_profile}",
        "run_id": f"build_daily_digest__{run_timestamp(run_id)}__{delivery_profile}",
        "digest_date": run_date,
        "delivery_profile": delivery_profile,
        "generated_at": now_iso(),
        "story_ids": story_ids,
        "context_refs": daily.get("context_refs", []),
        "markdown_path": markdown_path,
    })
    return daily


def build_digest_manifest(
    run_id: str,
    run_date: str,
    delivery_profile: str,
    brief_path: str,
    markdown_path: str,
    draft: dict,
) -> dict:
    timestamp = run_timestamp(run_id)
    full_run_id = f"build_daily_digest__{timestamp}__{delivery_profile}"
    render_metadata = draft["daily_brief"].get("render_metadata", {})
    digest_status = render_metadata.get("digest_status", "non_canonical_digest")
    return {
        "run_id": full_run_id,
        "mode": "build_daily_digest",
        "started_at": now_iso(),
        "finished_at": now_iso(),
        "status": "completed",
        "inputs": [brief_path],
        "outputs": [markdown_path, brief_path],
        "delivery_profile": delivery_profile,
        "counts": {
            "story_count": len(draft["enriched_items"]),
            "top_story_count": len(draft["daily_brief"].get("top_story_ids", [])),
            "weak_signal_count": len(draft["daily_brief"].get("weak_signal_ids", [])),
        },
        "warnings": [],
        "errors": [],
        "operator_report": {
            "digest_generation": {
                "status": "generated",
                "digest_status": digest_status,
                "canonical": digest_status == "canonical_digest",
            },
            "qa_review": draft.get("qa_review", {"status": "skipped"}),
            "telegram_delivery": draft.get("telegram_delivery", {"status": "skipped", "delivered": False}),
        },
        "notes": [f"Materialized by stage_c_finish for {run_date}."],
    }


def materialize_finish(
    *,
    repo_root: pathlib.Path,
    run_id: str,
    run_date: str,
    source_group: str,
    delivery_profile: str,
    shortlist_path: pathlib.Path,
    article_prefetch_result_path: pathlib.Path,
    draft_path: pathlib.Path,
) -> dict:
    repo_root = repo_root.resolve()
    timestamp = run_timestamp(run_id)
    shortlist_path = shortlist_path.resolve()
    article_prefetch_result_path = article_prefetch_result_path.resolve()
    draft_path = draft_path.resolve()
    draft = read_json(draft_path)
    shortlisted_urls = load_shortlisted_urls(shortlist_path)
    prefetch_by_url = load_prefetch_by_url(article_prefetch_result_path)
    validate_draft(draft, run_id, run_date, source_group, delivery_profile, shortlisted_urls, prefetch_by_url)

    enriched_path = repo_root / ".state" / "enriched" / run_date / f"scrape_and_enrich__{timestamp}__{source_group}.json"
    scrape_manifest_path = repo_root / ".state" / "runs" / run_date / f"scrape_and_enrich__{timestamp}__{source_group}.json"
    brief_path = repo_root / ".state" / "briefs" / "daily" / f"{run_date}__{delivery_profile}.json"
    digest_manifest_path = repo_root / ".state" / "runs" / run_date / f"build_daily_digest__{timestamp}__{delivery_profile}.json"
    markdown_path = repo_root / "digests" / f"{run_date}-daily-digest.md"
    summary_path = repo_root / ".state" / "codex-runs" / f"{run_id}-finish-summary.json"

    enriched_items = []
    for item in draft["enriched_items"]:
        enriched = dict(item)
        enriched["run_id"] = f"scrape_and_enrich__{timestamp}__{source_group}"
        enriched["enriched_at"] = now_iso()
        enriched_items.append(enriched)

    write_json(enriched_path, enriched_items)
    write_json(
        scrape_manifest_path,
        build_scrape_manifest(
            run_id,
            run_date,
            source_group,
            rel(enriched_path, repo_root),
            rel(article_prefetch_result_path, repo_root),
            enriched_items,
            [],
        ),
    )
    write_json(brief_path, build_daily_brief(draft, run_id, run_date, delivery_profile, rel(markdown_path, repo_root)))
    write_text(markdown_path, str(draft["digest_markdown"]))
    write_json(
        digest_manifest_path,
        build_digest_manifest(run_id, run_date, delivery_profile, rel(brief_path, repo_root), rel(markdown_path, repo_root), draft),
    )

    summary = {
        "status": "materialized",
        "run_id": run_id,
        "run_timestamp": timestamp,
        "run_date": run_date,
        "source_group": source_group,
        "delivery_profile": delivery_profile,
        "enriched_count": len(enriched_items),
        "outputs": {
            "enriched_path": rel(enriched_path, repo_root),
            "scrape_manifest_path": rel(scrape_manifest_path, repo_root),
            "daily_brief_path": rel(brief_path, repo_root),
            "digest_manifest_path": rel(digest_manifest_path, repo_root),
            "markdown_path": rel(markdown_path, repo_root),
            "summary_path": rel(summary_path, repo_root),
        },
    }
    write_json(summary_path, summary)
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize deterministic Stage C finish artifacts")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-date", required=True)
    parser.add_argument("--source-group", required=True)
    parser.add_argument("--delivery-profile", required=True)
    parser.add_argument("--shortlist-path", required=True)
    parser.add_argument("--article-prefetch-result", required=True)
    parser.add_argument("--draft-path", required=True)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    try:
        summary = materialize_finish(
            repo_root=pathlib.Path(args.repo_root),
            run_id=args.run_id,
            run_date=args.run_date,
            source_group=args.source_group,
            delivery_profile=args.delivery_profile,
            shortlist_path=pathlib.Path(args.shortlist_path),
            article_prefetch_result_path=pathlib.Path(args.article_prefetch_result),
            draft_path=pathlib.Path(args.draft_path),
        )
        if args.pretty:
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(summary, ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001
        print(f"stage c finish failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
