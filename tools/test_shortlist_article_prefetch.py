#!/usr/bin/env python3
"""
Offline contract tests for shortlist_article_prefetch.py.

Run with:
  python3 tools/test_shortlist_article_prefetch.py
"""
from __future__ import annotations

import io
import json
import pathlib
import sys
import tempfile
from contextlib import redirect_stdout
from contextlib import redirect_stderr

import shortlist_article_prefetch


def write_json(path: pathlib.Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def shortlist_item(**overrides: object) -> dict:
    item = {
        "run_id": "monitor_sources__20260504T120000Z__daily_core",
        "source_id": "example_source",
        "url": "https://example.test/article",
        "canonical_url": "https://example.test/article",
        "title": "Portal launches verified seller tools",
        "published": "2026-05-04",
        "triage_decision": "shortlist",
        "raw_snippet": "Public listing quality update.",
    }
    item.update(overrides)
    return item


def fake_fetch_batch(specs: list[dict], *, fetched_at: str | None = None) -> dict:
    assert [spec["url"] for spec in specs] == [
        "https://example.test/full",
        "https://example.test/paywall",
    ]
    return {
        "fetched_at": fetched_at or "2026-05-04T12:10:00Z",
        "batch_status": "partial_success",
        "failure_class": None,
        "run_failure": None,
        "summary_counts": {
            "full": 1,
            "snippet_fallback": 0,
            "paywall_stub": 1,
        },
        "results": [
            {
                "source_id": "example_source",
                "url": "https://example.test/full",
                "canonical_url": "https://example.test/full",
                "title": "Full Article",
                "published": "2026-05-04",
                "body_status_hint": "full",
                "text": "Full article body " * 80,
                "text_char_count": len("Full article body " * 80),
                "error": None,
                "failure_class": None,
                "soft_fail": None,
                "soft_fail_detail": None,
                "fetch_method": "static_http",
                "http": {"status": 200},
            },
            {
                "source_id": "example_source",
                "url": "https://example.test/paywall",
                "canonical_url": "https://example.test/paywall",
                "title": "Paywall Article",
                "published": "2026-05-04",
                "body_status_hint": "paywall_stub",
                "text": "",
                "text_char_count": 0,
                "error": None,
                "failure_class": "blocked_or_paywall",
                "soft_fail": "blocked_or_paywall",
                "soft_fail_detail": "http_403_observed",
                "fetch_method": "static_http",
                "http": {"status": 403},
            },
        ],
    }


def test_prefetch_fetches_only_shortlisted_items_and_writes_outputs() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = pathlib.Path(tmpdir)
        shortlist_path = repo_root / ".state/shortlists/2026-05-04/monitor_sources__20260504T120000Z__daily_core.json"
        write_json(
            shortlist_path,
            [
                shortlist_item(url="https://example.test/full", canonical_url="https://example.test/full", title="Full Article"),
                shortlist_item(url="https://example.test/paywall", canonical_url="https://example.test/paywall", title="Paywall Article"),
                shortlist_item(
                    url="https://example.test/drop",
                    canonical_url="https://example.test/drop",
                    title="Dropped Article",
                    triage_decision="drop",
                ),
            ],
        )

        doc = shortlist_article_prefetch.run_prefetch(
            shortlist_path=shortlist_path,
            run_id="20260504T121000Z-weekday_digest",
            repo_root=repo_root,
            fetch_batch=fake_fetch_batch,
            fetched_at="2026-05-04T12:10:00Z",
        )

        summary = doc["summary"]
        assert summary["shortlisted_count"] == 2
        assert summary["attempted_count"] == 2
        assert summary["full_count"] == 1
        assert summary["snippet_fallback_count"] == 0
        assert summary["paywall_stub_count"] == 1
        assert summary["result_path"] == ".state/codex-runs/20260504T121000Z-weekday_digest-article-prefetch-result.json"
        assert summary["summary_path"] == ".state/codex-runs/20260504T121000Z-weekday_digest-article-prefetch-summary.json"

        full_entry = doc["results"][0]
        paywall_entry = doc["results"][1]
        assert full_entry["article_file"] == ".state/articles/2026-05/2026-05-04_full-article.md"
        assert full_entry["body_status_hint"] == "full"
        assert paywall_entry["article_file"] is None
        assert paywall_entry["body_status_hint"] == "paywall_stub"

        article_path = repo_root / full_entry["article_file"]
        assert article_path.exists()
        article_text = article_path.read_text(encoding="utf-8")
        assert "source_id: example_source" in article_text
        assert "body_status_hint: full" in article_text
        assert "Full article body" in article_text
        assert not (repo_root / ".state/articles/2026-05/2026-05-04_dropped-article.md").exists()

        assert (repo_root / summary["result_path"]).exists()
        assert (repo_root / summary["summary_path"]).exists()


def test_slug_collision_appends_suffix_for_same_date_and_title() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = pathlib.Path(tmpdir)
        first = {
            "source_id": "one",
            "url": "https://example.test/one",
            "canonical_url": "https://example.test/one",
            "title": "Same Title",
            "published": "2026-05-04",
            "body_status_hint": "full",
            "text": "One " * 200,
            "text_char_count": 800,
            "error": None,
            "failure_class": None,
            "soft_fail": None,
            "soft_fail_detail": None,
            "fetch_method": "static_http",
            "http": {"status": 200},
        }
        second = dict(first, source_id="two", url="https://example.test/two", canonical_url="https://example.test/two")

        entries = shortlist_article_prefetch.write_article_artifacts(
            results=[first, second],
            repo_root=repo_root,
            fetched_at="2026-05-04T12:10:00Z",
        )

        assert entries[0]["article_file"] == ".state/articles/2026-05/2026-05-04_same-title.md"
        assert entries[1]["article_file"] == ".state/articles/2026-05/2026-05-04_same-title-2.md"
        assert (repo_root / entries[0]["article_file"]).exists()
        assert (repo_root / entries[1]["article_file"]).exists()


def test_inman_snippet_fallback_with_visible_text_writes_article_file() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = pathlib.Path(tmpdir)
        result = {
            "source_id": "inman_tech_innovation",
            "url": "https://www.inman.com/2026/05/01/example/",
            "canonical_url": "https://www.inman.com/2026/05/01/example",
            "title": "Real estate has an AI problem",
            "published": "2026-05-01",
            "body_status_hint": "snippet_fallback",
            "text": "Public Inman article text visible before the subscription prompt.",
            "text_char_count": 62,
            "error": None,
            "failure_class": "blocked_or_paywall",
            "soft_fail": "blocked_or_paywall",
            "soft_fail_detail": "public_partial_text_extracted",
            "fetch_method": "static_http",
            "http": {"status": 200},
        }

        entries = shortlist_article_prefetch.write_article_artifacts(
            results=[result],
            repo_root=repo_root,
            fetched_at="2026-05-04T12:10:00Z",
        )

        assert entries[0]["body_status_hint"] == "snippet_fallback"
        assert entries[0]["article_file"] == ".state/articles/2026-05/2026-05-01_real-estate-has-an-ai-problem.md"
        article_path = repo_root / entries[0]["article_file"]
        assert article_path.exists()
        article_text = article_path.read_text(encoding="utf-8")
        assert "body_status_hint: snippet_fallback" in article_text
        assert "Public Inman article text visible" in article_text


def test_cli_requires_explicit_shortlist_path() -> None:
    stderr = io.StringIO()
    try:
        with redirect_stderr(stderr):
            shortlist_article_prefetch.main(["--run-id", "20260504T121000Z-weekday_digest"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("CLI should require --shortlist-path")
    assert "--shortlist-path" in stderr.getvalue()


def test_cli_writes_summary_json_to_stdout() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = pathlib.Path(tmpdir)
        shortlist_path = repo_root / ".state/shortlists/2026-05-04/monitor_sources__20260504T120000Z__daily_core.json"
        write_json(
            shortlist_path,
            [
                shortlist_item(url="https://example.test/full", canonical_url="https://example.test/full", title="Full Article"),
                shortlist_item(url="https://example.test/paywall", canonical_url="https://example.test/paywall", title="Paywall Article"),
            ],
        )
        original = shortlist_article_prefetch.article_fetch.fetch_batch
        stdout = io.StringIO()
        shortlist_article_prefetch.article_fetch.fetch_batch = fake_fetch_batch
        try:
            with redirect_stdout(stdout):
                shortlist_article_prefetch.main(
                    [
                        "--repo-root",
                        str(repo_root),
                        "--shortlist-path",
                        str(shortlist_path),
                        "--run-id",
                        "20260504T121000Z-weekday_digest",
                        "--fetched-at",
                        "2026-05-04T12:10:00Z",
                    ]
                )
        finally:
            shortlist_article_prefetch.article_fetch.fetch_batch = original

        doc = json.loads(stdout.getvalue())
        assert doc["shortlisted_count"] == 2
        assert doc["full_count"] == 1
        assert doc["summary_path"] == ".state/codex-runs/20260504T121000Z-weekday_digest-article-prefetch-summary.json"


def main() -> None:
    tests = [
        test_prefetch_fetches_only_shortlisted_items_and_writes_outputs,
        test_slug_collision_appends_suffix_for_same_date_and_title,
        test_inman_snippet_fallback_with_visible_text_writes_article_file,
        test_cli_requires_explicit_shortlist_path,
        test_cli_writes_summary_json_to_stdout,
    ]
    for test in tests:
        test()
    print(f"{len(tests)} tests passed")


if __name__ == "__main__":
    main()
