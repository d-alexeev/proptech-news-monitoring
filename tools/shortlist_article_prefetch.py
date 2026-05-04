#!/usr/bin/env python3
"""
shortlist_article_prefetch.py — current-run shortlist article prefetch helper.

This runner helper reads one explicit shortlist shard, fetches only items with
triage_decision=shortlist, writes full article bodies as bounded artifacts, and
writes compact result/summary manifests for scrape_and_enrich.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import article_fetch


FetchBatch = Callable[..., dict]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _repo_relative(path: Path, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _coerce_items(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("shortlisted_items", "items", "shortlist", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    raise ValueError("shortlist shard must be a JSON array or object with a shortlist array")


def _shortlisted_items(shortlist_path: Path) -> list[dict]:
    return [
        item
        for item in _coerce_items(_read_json(shortlist_path))
        if item.get("triage_decision") == "shortlist"
    ]


def _article_spec(item: dict) -> dict:
    return {
        "source_id": item.get("source_id") or "",
        "url": item.get("url") or "",
        "canonical_url": item.get("canonical_url") or item.get("url") or "",
        "title": item.get("title") or "",
        "published": item.get("published"),
        "shortlist_run_id": item.get("run_id") or item.get("shortlist_run_id"),
    }


def _slug(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized.lower()).strip("-")
    return slug[:80].strip("-") or "article"


def _safe_frontmatter_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\n", " ").strip()


def _published_date(result: dict, fetched_at: str) -> str:
    published = result.get("published")
    if isinstance(published, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", published):
        return published
    return fetched_at[:10] if re.match(r"^\d{4}-\d{2}-\d{2}", fetched_at) else "unknown-date"


def _article_file_path(result: dict, repo_root: Path, fetched_at: str, used_paths: set[Path]) -> Path:
    date = _published_date(result, fetched_at)
    month = date[:7] if re.match(r"^\d{4}-\d{2}", date) else "unknown-month"
    base_slug = _slug(result.get("title") or result.get("canonical_url") or result.get("url") or "article")
    articles_dir = repo_root / ".state" / "articles" / month
    candidate = articles_dir / f"{date}_{base_slug}.md"
    suffix = 2
    while candidate in used_paths or candidate.exists():
        candidate = articles_dir / f"{date}_{base_slug}-{suffix}.md"
        suffix += 1
    used_paths.add(candidate)
    return candidate


def _article_markdown(result: dict, *, fetched_at: str) -> str:
    frontmatter_keys = [
        "source_id",
        "url",
        "canonical_url",
        "title",
        "published",
        "body_status_hint",
    ]
    lines = ["---"]
    for key in frontmatter_keys:
        lines.append(f"{key}: {_safe_frontmatter_value(result.get(key))}")
    lines.append(f"fetched_at: {fetched_at}")
    lines.append("---")
    lines.append("")
    lines.append(result.get("text") or "")
    lines.append("")
    return "\n".join(lines)


def _should_write_article_file(result: dict) -> bool:
    if not result.get("text"):
        return False
    if result.get("body_status_hint") == "full":
        return True
    return (
        result.get("source_id") == "inman_tech_innovation"
        and result.get("body_status_hint") == "snippet_fallback"
        and result.get("soft_fail_detail") == "public_partial_text_extracted"
    )


def _manifest_entry(result: dict, article_file: str | None) -> dict:
    return {
        "source_id": result.get("source_id") or "",
        "url": result.get("url") or "",
        "canonical_url": result.get("canonical_url") or result.get("url") or "",
        "title": result.get("title") or "",
        "published": result.get("published"),
        "body_status_hint": result.get("body_status_hint") or "snippet_fallback",
        "article_file": article_file,
        "fetch_method": result.get("fetch_method"),
        "text_char_count": result.get("text_char_count") or 0,
        "error": result.get("error"),
        "failure_class": result.get("failure_class"),
        "soft_fail": result.get("soft_fail"),
        "soft_fail_detail": result.get("soft_fail_detail"),
        "http": result.get("http"),
    }


def write_article_artifacts(
    *,
    results: list[dict],
    repo_root: Path,
    fetched_at: str,
) -> list[dict]:
    entries: list[dict] = []
    used_paths: set[Path] = set()
    for result in results:
        article_file = None
        if _should_write_article_file(result):
            path = _article_file_path(result, repo_root, fetched_at, used_paths)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(_article_markdown(result, fetched_at=fetched_at), encoding="utf-8")
            article_file = _repo_relative(path, repo_root)
        entries.append(_manifest_entry(result, article_file))
    return entries


def _summary(
    *,
    shortlisted_count: int,
    results: list[dict],
    result_path: Path,
    summary_path: Path,
    repo_root: Path,
    fetched_at: str,
    batch_doc: dict,
) -> dict:
    return {
        "fetched_at": fetched_at,
        "shortlisted_count": shortlisted_count,
        "attempted_count": len(results),
        "full_count": sum(1 for result in results if result.get("body_status_hint") == "full"),
        "snippet_fallback_count": sum(
            1 for result in results if result.get("body_status_hint") == "snippet_fallback"
        ),
        "paywall_stub_count": sum(1 for result in results if result.get("body_status_hint") == "paywall_stub"),
        "batch_status": batch_doc.get("batch_status"),
        "failure_class": batch_doc.get("failure_class"),
        "run_failure": batch_doc.get("run_failure"),
        "result_path": _repo_relative(result_path, repo_root),
        "summary_path": _repo_relative(summary_path, repo_root),
    }


def run_prefetch(
    *,
    shortlist_path: Path,
    run_id: str,
    repo_root: Path,
    fetch_batch: FetchBatch | None = None,
    fetched_at: str | None = None,
) -> dict:
    repo_root = repo_root.resolve()
    shortlist_path = shortlist_path if shortlist_path.is_absolute() else repo_root / shortlist_path
    shortlist_path = shortlist_path.resolve()
    if not shortlist_path.exists():
        raise FileNotFoundError(f"shortlist shard does not exist: {shortlist_path}")

    fetched_at_value = fetched_at or _now_iso()
    items = _shortlisted_items(shortlist_path)
    specs = [_article_spec(item) for item in items if item.get("url")]
    fetcher = fetch_batch or article_fetch.fetch_batch
    batch_doc = fetcher(specs, fetched_at=fetched_at_value)
    fetched_at_value = batch_doc.get("fetched_at") or fetched_at_value
    results = batch_doc.get("results") or []

    entries = write_article_artifacts(results=results, repo_root=repo_root, fetched_at=fetched_at_value)

    result_path = repo_root / ".state" / "codex-runs" / f"{run_id}-article-prefetch-result.json"
    summary_path = repo_root / ".state" / "codex-runs" / f"{run_id}-article-prefetch-summary.json"
    summary = _summary(
        shortlisted_count=len(items),
        results=entries,
        result_path=result_path,
        summary_path=summary_path,
        repo_root=repo_root,
        fetched_at=fetched_at_value,
        batch_doc=batch_doc,
    )
    result_doc = {
        "run_id": run_id,
        "shortlist_path": _repo_relative(shortlist_path, repo_root),
        "fetched_at": fetched_at_value,
        "batch_status": batch_doc.get("batch_status"),
        "failure_class": batch_doc.get("failure_class"),
        "run_failure": batch_doc.get("run_failure"),
        "summary": summary,
        "results": entries,
    }

    _write_json(result_path, result_doc)
    _write_json(summary_path, summary)
    return result_doc


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prefetch article bodies for a current-run shortlist shard")
    parser.add_argument("--repo-root", default=".", help="Repository root where .state artifacts are written")
    parser.add_argument("--shortlist-path", required=True, help="Explicit current-run shortlist shard path")
    parser.add_argument("--run-id", required=True, help="Runner run id used for manifest filenames")
    parser.add_argument("--fetched-at", help="Stable ISO timestamp for tests/replay")
    parser.add_argument("--pretty", action="store_true", help="Indent stdout JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    try:
        doc = run_prefetch(
            shortlist_path=Path(args.shortlist_path),
            run_id=args.run_id,
            repo_root=Path(args.repo_root),
            fetched_at=args.fetched_at,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"article prefetch failed: {exc}", file=sys.stderr)
        sys.exit(1)

    indent = 2 if args.pretty else None
    sys.stdout.write(json.dumps(doc["summary"], ensure_ascii=False, indent=indent))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
