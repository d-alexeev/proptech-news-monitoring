#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rel(path: pathlib.Path, repo_root: pathlib.Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def read_json(path: pathlib.Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: pathlib.Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def coerce_items(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("shortlisted_items", "items", "shortlist", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    raise ValueError("shortlist shard must be a JSON array or an object containing a shortlist array")


def shortlisted_items(shortlist_path: pathlib.Path) -> list[dict]:
    return [
        item
        for item in coerce_items(read_json(shortlist_path))
        if item.get("triage_decision") == "shortlist"
    ]


def _shortlist_dir(repo_root: pathlib.Path, run_date: str) -> pathlib.Path:
    return repo_root / ".state" / "shortlists" / run_date


def _shortlist_glob(source_group: str) -> str:
    return f"monitor_sources__*__{source_group}.json"


def find_latest_shortlist(*, repo_root: pathlib.Path, run_date: str, source_group: str) -> pathlib.Path:
    base = _shortlist_dir(repo_root, run_date)
    matches = sorted(base.glob(_shortlist_glob(source_group)))
    if not matches:
        raise FileNotFoundError(f"no shortlist shard found for {run_date} source group {source_group}")
    return matches[-1]


def snapshot_shortlists(*, repo_root: pathlib.Path, run_date: str, source_group: str) -> set[str]:
    base = _shortlist_dir(repo_root, run_date)
    return {
        path.resolve().as_posix()
        for path in base.glob(_shortlist_glob(source_group))
    }


def find_new_shortlist(
    *,
    repo_root: pathlib.Path,
    run_date: str,
    source_group: str,
    before_paths: set[str],
) -> pathlib.Path:
    base = _shortlist_dir(repo_root, run_date)
    matches = sorted(
        path
        for path in base.glob(_shortlist_glob(source_group))
        if path.resolve().as_posix() not in before_paths
    )
    if not matches:
        raise FileNotFoundError(f"no new shortlist shard found for {run_date} source group {source_group}")
    return matches[-1]


def synthetic_entry(item: dict, reason: str) -> dict:
    return {
        "source_id": item.get("source_id") or "",
        "url": item.get("url") or "",
        "canonical_url": item.get("canonical_url") or item.get("url") or "",
        "title": item.get("title") or "",
        "published": item.get("published"),
        "body_status_hint": "snippet_fallback",
        "article_file": None,
        "fetch_method": "synthetic_fallback",
        "text_char_count": 0,
        "error": None,
        "failure_class": "article_prefetch_unavailable",
        "soft_fail": reason,
        "soft_fail_detail": reason,
        "http": None,
    }


def write_synthetic_article_prefetch(
    *,
    repo_root: pathlib.Path,
    run_id: str,
    shortlist_path: pathlib.Path,
    reason: str,
    fetched_at: str | None = None,
) -> dict:
    repo_root = repo_root.resolve()
    shortlist_path = shortlist_path.resolve()
    fetched_at_value = fetched_at or now_iso()
    entries = [synthetic_entry(item, reason) for item in shortlisted_items(shortlist_path)]
    result_path = repo_root / ".state" / "codex-runs" / f"{run_id}-article-prefetch-result.json"
    summary_path = repo_root / ".state" / "codex-runs" / f"{run_id}-article-prefetch-summary.json"
    summary = {
        "fetched_at": fetched_at_value,
        "shortlisted_count": len(entries),
        "attempted_count": 0,
        "full_count": 0,
        "snippet_fallback_count": len(entries),
        "paywall_stub_count": 0,
        "batch_status": "synthetic_fallback",
        "failure_class": "article_prefetch_unavailable",
        "run_failure": reason,
        "result_path": rel(result_path, repo_root),
        "summary_path": rel(summary_path, repo_root),
    }
    doc = {
        "run_id": run_id,
        "shortlist_path": rel(shortlist_path, repo_root),
        "fetched_at": fetched_at_value,
        "batch_status": "synthetic_fallback",
        "failure_class": "article_prefetch_unavailable",
        "run_failure": reason,
        "summary": summary,
        "results": entries,
    }
    write_json(result_path, doc)
    write_json(summary_path, summary)
    return doc


def parse_before_json(raw: str) -> set[str]:
    value = json.loads(raw)
    if not isinstance(value, list):
        raise ValueError("--before-json must be a JSON array")
    return {str(item) for item in value}


def run_timestamp(run_id: str) -> str:
    return run_id.split("-", 1)[0]


def validate_finish_artifacts(
    *,
    repo_root: pathlib.Path,
    run_id: str,
    run_date: str,
    source_group: str,
    delivery_profile: str,
    require_finish_summary: bool = False,
) -> dict:
    repo_root = repo_root.resolve()
    timestamp = run_timestamp(run_id)
    required_paths = [
        repo_root / ".state" / "enriched" / run_date / f"scrape_and_enrich__{timestamp}__{source_group}.json",
        repo_root / ".state" / "runs" / run_date / f"scrape_and_enrich__{timestamp}__{source_group}.json",
        repo_root / ".state" / "runs" / run_date / f"build_daily_digest__{timestamp}__{delivery_profile}.json",
        repo_root / ".state" / "briefs" / "daily" / f"{run_date}__{delivery_profile}.json",
    ]
    if require_finish_summary:
        required_paths.append(repo_root / ".state" / "codex-runs" / f"{run_id}-finish-summary.json")
    missing = [path for path in required_paths if not path.exists()]
    if missing:
        missing_text = ", ".join(rel(path, repo_root) for path in missing)
        raise FileNotFoundError(f"missing current-run finish artifacts: {missing_text}")
    return {
        "status": "ok",
        "run_id": run_id,
        "run_timestamp": timestamp,
        "required_paths": [rel(path, repo_root) for path in required_paths],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Codex schedule artifact helpers")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common_shortlist_args(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--repo-root", required=True)
        subparser.add_argument("--run-date", required=True)
        subparser.add_argument("--source-group", required=True)

    snapshot = subparsers.add_parser("snapshot-shortlists", help="Print current shortlist shard paths")
    add_common_shortlist_args(snapshot)

    find_latest = subparsers.add_parser("find-shortlist", help="Print latest shortlist shard path")
    add_common_shortlist_args(find_latest)

    find_new = subparsers.add_parser("find-new-shortlist", help="Print newest shortlist shard not in snapshot")
    add_common_shortlist_args(find_new)
    find_new.add_argument("--before-json", required=True)

    synthetic = subparsers.add_parser("synthetic-article-prefetch", help="Write synthetic article prefetch fallback")
    synthetic.add_argument("--repo-root", required=True)
    synthetic.add_argument("--run-id", required=True)
    synthetic.add_argument("--shortlist-path", required=True)
    synthetic.add_argument("--reason", required=True)
    synthetic.add_argument("--fetched-at")

    validate_finish = subparsers.add_parser("validate-finish-artifacts", help="Validate Stage C current-run artifacts")
    validate_finish.add_argument("--repo-root", required=True)
    validate_finish.add_argument("--run-id", required=True)
    validate_finish.add_argument("--run-date", required=True)
    validate_finish.add_argument("--source-group", required=True)
    validate_finish.add_argument("--delivery-profile", required=True)
    validate_finish.add_argument("--require-finish-summary", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    repo_root = pathlib.Path(args.repo_root)
    try:
        if args.command == "snapshot-shortlists":
            paths = sorted(snapshot_shortlists(
                repo_root=repo_root,
                run_date=args.run_date,
                source_group=args.source_group,
            ))
            print(json.dumps(paths, ensure_ascii=False))
        elif args.command == "find-shortlist":
            print(find_latest_shortlist(
                repo_root=repo_root,
                run_date=args.run_date,
                source_group=args.source_group,
            ).resolve().as_posix())
        elif args.command == "find-new-shortlist":
            print(find_new_shortlist(
                repo_root=repo_root,
                run_date=args.run_date,
                source_group=args.source_group,
                before_paths=parse_before_json(args.before_json),
            ).resolve().as_posix())
        elif args.command == "synthetic-article-prefetch":
            doc = write_synthetic_article_prefetch(
                repo_root=repo_root,
                run_id=args.run_id,
                shortlist_path=pathlib.Path(args.shortlist_path),
                reason=args.reason,
                fetched_at=args.fetched_at,
            )
            print(json.dumps(doc["summary"], ensure_ascii=False))
        elif args.command == "validate-finish-artifacts":
            validation = validate_finish_artifacts(
                repo_root=repo_root,
                run_id=args.run_id,
                run_date=args.run_date,
                source_group=args.source_group,
                delivery_profile=args.delivery_profile,
                require_finish_summary=args.require_finish_summary,
            )
            print(json.dumps(validation, ensure_ascii=False))
        else:
            raise ValueError(f"unknown command: {args.command}")
    except Exception as exc:  # noqa: BLE001
        print(f"schedule artifact helper failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
