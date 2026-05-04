#!/usr/bin/env python3
"""
Offline tests for source_discovery_prefetch.py.

Run with:
  python3 tools/test_source_discovery_prefetch.py
"""
from __future__ import annotations

import json
import pathlib
import tempfile

import source_discovery_prefetch as prefetch


def write_fixture_repo(root: pathlib.Path) -> None:
    config = root / "config/runtime"
    (config / "source-groups").mkdir(parents=True)
    (root / "tools").mkdir()
    (root / ".state/codex-runs").mkdir(parents=True)
    (config / "schedule_bindings.yaml").write_text(
        "weekday_digest:\n"
        "  source_groups: [daily_core]\n"
        "  delivery_profile: telegram_digest\n",
        encoding="utf-8",
    )
    (config / "source-groups/daily_core.yaml").write_text(
        "group_id: daily_core\n"
        "sources:\n"
        "  - id: rss_source\n"
        "    fetch_strategy: rss\n"
        "    rss_feed: https://feeds.example.test/rss.xml\n"
        "  - id: html_source\n"
        "    fetch_strategy: html_scrape\n"
        "    landing_urls:\n"
        "      - https://html.example.test/news\n"
        "  - id: browser_source\n"
        "    fetch_strategy: chrome_scrape\n"
        "    landing_urls:\n"
        "      - https://browser.example.test/\n",
        encoding="utf-8",
    )


def test_build_source_specs_maps_static_and_browser_sources() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        write_fixture_repo(root)

        plan = prefetch.build_prefetch_plan(root, "weekday_digest")

    assert plan["schedule_id"] == "weekday_digest"
    assert plan["source_groups"] == ["daily_core"]
    assert plan["fetchable_source_count"] == 2
    assert plan["browser_source_count"] == 1
    assert plan["source_specs"] == [
        {
            "source_id": "rss_source",
            "url": "https://feeds.example.test/rss.xml",
            "kind": "rss",
            "source_group": "daily_core",
            "fetch_strategy": "rss",
        },
        {
            "source_id": "html_source",
            "url": "https://html.example.test/news",
            "kind": "http",
            "source_group": "daily_core",
            "fetch_strategy": "html_scrape",
        },
    ]
    assert plan["browser_source_specs"] == [
        {
            "source_id": "browser_source",
            "source_group": "daily_core",
            "fetch_strategy": "chrome_scrape",
            "url": "https://browser.example.test/",
        }
    ]
    assert plan["skipped_sources"] == []


def test_run_prefetch_writes_artifacts_and_summarizes_partial_source_discovery() -> None:
    fetch_doc = {
        "fetched_at": "2026-05-04T10:00:00Z",
        "batch_status": "failed",
        "failure_class": None,
        "run_failure": None,
        "results": [
            {
                "source_id": "rss_source",
                "items": [{"title": "One"}],
                "body": None,
                "error": None,
                "failure_class": None,
                "soft_fail": None,
            },
            {
                "source_id": "html_source",
                "items": [],
                "body": None,
                "error": "network_error",
                "failure_class": "dns_resolution",
                "soft_fail": None,
            },
        ],
    }

    def fake_fetch(_: list[dict], ___: pathlib.Path) -> tuple[int, dict, str]:
        return 1, fetch_doc, "diagnostic stderr"

    def fake_dns(hosts: list[str]) -> dict:
        return {host: {"ok": True, "addr": "127.0.0.1"} for host in hosts}

    browser_doc = {
        "fetched_at": "2026-05-04T10:00:01Z",
        "batch_status": "success",
        "failure_class": None,
        "run_failure": None,
        "results": [
            {
                "source_id": "browser_source",
                "text": "Visible browser evidence",
                "error": None,
                "failure_class": None,
                "soft_fail": None,
            }
        ],
    }

    def fake_browser(_: list[dict], ___: pathlib.Path) -> tuple[int, dict, str]:
        return 0, browser_doc, ""

    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        write_fixture_repo(root)

        summary = prefetch.run_prefetch(
            root,
            "weekday_digest",
            run_id="20260504T100000Z-weekday_digest",
            fetch_runner=fake_fetch,
            browser_runner=fake_browser,
            dns_checker=fake_dns,
        )

        fetch_path = root / summary["fetch_result_path"]
        browser_path = root / summary["browser_result_path"]
        dns_path = root / summary["dns_check_path"]
        summary_path = root / summary["summary_path"]

        assert fetch_path.exists()
        assert browser_path.exists()
        assert dns_path.exists()
        assert summary_path.exists()
        assert json.loads(fetch_path.read_text(encoding="utf-8"))["batch_status"] == "failed"
        assert json.loads(browser_path.read_text(encoding="utf-8"))["batch_status"] == "success"
        assert json.loads(dns_path.read_text(encoding="utf-8"))["example.com"]["ok"] is True
        assert json.loads(summary_path.read_text(encoding="utf-8"))["source_discovery_status"] == "partial"

    assert summary["source_discovery_status"] == "partial"
    assert summary["fetchable_source_count"] == 2
    assert summary["fetchable_attempted_count"] == 2
    assert summary["fetchable_success_count"] == 1
    assert summary["browser_source_count"] == 1
    assert summary["browser_attempted_count"] == 1
    assert summary["browser_success_count"] == 1
    assert summary["browser_batch_status"] == "success"
    assert summary["skipped_sources"] == []
    assert summary["runner_invocation"]["exit_code"] == 1


def test_run_prefetch_preserves_global_dns_failure_as_blocked() -> None:
    fetch_doc = {
        "fetched_at": "2026-05-04T10:00:00Z",
        "batch_status": "environment_failure",
        "failure_class": "global_dns_resolution_failure",
        "run_failure": {"failure_type": "dns_resolution"},
        "results": [],
    }

    def fake_fetch(_: list[dict], ___: pathlib.Path) -> tuple[int, dict, str]:
        return 1, fetch_doc, ""

    def fake_dns(hosts: list[str]) -> dict:
        return {host: {"ok": False, "error": "gaierror"} for host in hosts}

    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        write_fixture_repo(root)

        summary = prefetch.run_prefetch(
            root,
            "weekday_digest",
            run_id="20260504T100000Z-weekday_digest",
            fetch_runner=fake_fetch,
            dns_checker=fake_dns,
        )

    assert summary["source_discovery_status"] == "failed"
    assert summary["failure_class"] == "global_dns_resolution_failure"
    assert summary["downstream_gate"] == "blocked_before_digest"
    assert summary["canonical_static_source_complete"] is False


def test_run_prefetch_records_browser_runtime_unavailable_as_skipped() -> None:
    fetch_doc = {
        "fetched_at": "2026-05-04T10:00:00Z",
        "batch_status": "success",
        "failure_class": None,
        "run_failure": None,
        "results": [
            {
                "source_id": "rss_source",
                "items": [{"title": "One"}],
                "body": None,
                "error": None,
                "failure_class": None,
                "soft_fail": None,
            }
        ],
    }

    browser_doc = {
        "fetched_at": "2026-05-04T10:00:01Z",
        "batch_status": "environment_failure",
        "failure_class": "browser_runtime_unavailable",
        "run_failure": {"failure_type": "browser_runtime_unavailable"},
        "results": [
            {
                "source_id": "browser_source",
                "error": "browser_runtime_unavailable: missing",
                "failure_class": "browser_runtime_unavailable",
                "soft_fail": None,
            }
        ],
    }

    def fake_fetch(_: list[dict], ___: pathlib.Path) -> tuple[int, dict, str]:
        return 0, fetch_doc, ""

    def fake_browser(_: list[dict], ___: pathlib.Path) -> tuple[int, dict, str]:
        return 1, browser_doc, "playwright missing"

    def fake_dns(hosts: list[str]) -> dict:
        return {host: {"ok": True, "addr": "127.0.0.1"} for host in hosts}

    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        write_fixture_repo(root)

        summary = prefetch.run_prefetch(
            root,
            "weekday_digest",
            run_id="20260504T100000Z-weekday_digest",
            fetch_runner=fake_fetch,
            browser_runner=fake_browser,
            dns_checker=fake_dns,
        )

    assert summary["source_discovery_status"] == "partial"
    assert summary["browser_attempted_count"] == 1
    assert summary["browser_success_count"] == 0
    assert summary["browser_batch_status"] == "environment_failure"
    assert summary["browser_failure_class"] == "browser_runtime_unavailable"
    assert summary["skipped_sources"] == [
        {
            "source_id": "browser_source",
            "source_group": "daily_core",
            "fetch_strategy": "chrome_scrape",
            "status": "not_attempted",
            "reason": "no_headless_browser_runner",
            "urls": ["https://browser.example.test/"],
        }
    ]


def main() -> None:
    tests = [
        test_build_source_specs_maps_static_and_browser_sources,
        test_run_prefetch_writes_artifacts_and_summarizes_partial_source_discovery,
        test_run_prefetch_preserves_global_dns_failure_as_blocked,
        test_run_prefetch_records_browser_runtime_unavailable_as_skipped,
    ]
    for test in tests:
        test()
    print(f"{len(tests)} tests passed")


if __name__ == "__main__":
    main()
