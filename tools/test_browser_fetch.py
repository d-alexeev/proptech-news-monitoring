#!/usr/bin/env python3
"""
Offline contract tests for browser_fetch.py.

Run with:
  python3 tools/test_browser_fetch.py
"""
from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout

import browser_fetch


def fake_browser_runner(spec: dict) -> dict:
    return {
        "status_like": 200,
        "content_type": "text/html",
        "final_url": spec["url"] + "?rendered=1",
        "elapsed_ms": 123,
        "text": " ".join(["Visible listing text"] * 600),
        "html": "<main>small fragment</main>",
    }


def test_fetch_source_rejects_non_chrome_scrape_strategy() -> None:
    result = browser_fetch.fetch_source(
        {
            "source_id": "redfin_news",
            "source_group": "daily_core",
            "fetch_strategy": "rss",
            "url": "https://www.redfin.com/news/",
        },
        browser_runner=fake_browser_runner,
    )

    assert result["source_id"] == "redfin_news"
    assert result["kind"] == "browser"
    assert result["http"] is None
    assert result["items"] == []
    assert result["text"] == ""
    assert result["html"] is None
    assert result["error"] == "unsupported fetch_strategy: rss"
    assert result["failure_class"] == "invalid_source_spec"
    assert result["soft_fail"] is None


def test_fetch_source_compacts_visible_text_and_emits_browser_metadata() -> None:
    result = browser_fetch.fetch_source(
        {
            "source_id": "similarweb_global_real_estate",
            "source_group": "daily_core",
            "fetch_strategy": "chrome_scrape",
            "url": "https://www.similarweb.com/website/zillow.com/#overview",
        },
        browser_runner=fake_browser_runner,
        max_text_chars=120,
    )

    assert result["source_id"] == "similarweb_global_real_estate"
    assert result["url"] == "https://www.similarweb.com/website/zillow.com/#overview"
    assert result["kind"] == "browser"
    assert result["http"] == {
        "status_like": 200,
        "content_type": "text/html",
        "source": "browser_observation",
    }
    assert result["final_url"].endswith("?rendered=1")
    assert result["elapsed_ms"] == 123
    assert len(result["text"]) <= 120
    assert result["text"].endswith("...")
    assert result["html"] == "<main>small fragment</main>"
    assert result["items"] == []
    assert result["error"] is None
    assert result["failure_class"] is None
    assert result["soft_fail"] is None
    assert result["browser"] == {
        "interface": "playwright",
        "mode": "headless",
        "headless": True,
        "user_agent_family": "chrome",
        "network_events_available": False,
    }


def test_missing_playwright_runtime_is_stable_environment_failure() -> None:
    def missing_runtime(_: dict) -> dict:
        raise browser_fetch.BrowserRuntimeUnavailable("playwright import failed")

    doc = browser_fetch.fetch_batch(
        [
            {
                "source_id": "onlinemarketplaces",
                "source_group": "daily_core",
                "fetch_strategy": "chrome_scrape",
                "url": "https://www.onlinemarketplaces.com/property-portal-insights/",
            }
        ],
        browser_runner=missing_runtime,
        fetched_at="2026-05-04T10:00:00Z",
    )

    assert doc["batch_status"] == "environment_failure"
    assert doc["failure_class"] == "browser_runtime_unavailable"
    assert doc["run_failure"]["failure_type"] == "browser_runtime_unavailable"
    assert doc["results"][0]["error"] == "browser_runtime_unavailable: playwright import failed"
    assert doc["results"][0]["failure_class"] == "browser_runtime_unavailable"


def test_cli_stdin_emits_one_json_document() -> None:
    payload = {
        "sources": [
            {
                "source_id": "similarweb_global_real_estate",
                "source_group": "daily_core",
                "fetch_strategy": "chrome_scrape",
                "url": "https://www.similarweb.com/website/zillow.com/#overview",
            }
        ]
    }

    original_stdin = sys.stdin
    original_runner = browser_fetch.DEFAULT_BROWSER_RUNNER
    stdout = io.StringIO()
    try:
        sys.stdin = io.StringIO(json.dumps(payload))
        browser_fetch.DEFAULT_BROWSER_RUNNER = fake_browser_runner
        with redirect_stdout(stdout):
            browser_fetch.main(["--stdin"])
    finally:
        sys.stdin = original_stdin
        browser_fetch.DEFAULT_BROWSER_RUNNER = original_runner

    doc = json.loads(stdout.getvalue())
    assert doc["batch_status"] == "success"
    assert doc["results"][0]["source_id"] == "similarweb_global_real_estate"


def main() -> None:
    tests = [
        test_fetch_source_rejects_non_chrome_scrape_strategy,
        test_fetch_source_compacts_visible_text_and_emits_browser_metadata,
        test_missing_playwright_runtime_is_stable_environment_failure,
        test_cli_stdin_emits_one_json_document,
    ]
    for test in tests:
        test()
    print(f"{len(tests)} tests passed")


if __name__ == "__main__":
    main()
