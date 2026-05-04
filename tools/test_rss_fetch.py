#!/usr/bin/env python3
"""
Offline contract tests for rss_fetch.py.

Run with:
  python3 tools/test_rss_fetch.py
"""
from __future__ import annotations

import os
import pathlib
import socket
import io
import json
import sys
import tempfile
import warnings
from contextlib import contextmanager
from contextlib import redirect_stdout
from typing import Iterator

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL.*")

import requests
from urllib3.exceptions import NameResolutionError

import rss_fetch


class FakeResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        text: str = "",
        url: str = "https://example.test/final",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.text = text
        self.url = url
        self.headers = headers or {}


@contextmanager
def fake_request(response_or_exc: FakeResponse | Exception) -> Iterator[None]:
    original = rss_fetch._do_request

    def _fake_do_request(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        if isinstance(response_or_exc, Exception):
            raise response_or_exc
        return response_or_exc

    rss_fetch._do_request = _fake_do_request
    try:
        yield
    finally:
        rss_fetch._do_request = original


INMAN_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Inman</title>
    <item>
      <guid>inman-tech-1</guid>
      <title>Brokerage launches AI home search pilot</title>
      <link>https://www.inman.com/2026/05/01/ai-home-search-pilot/</link>
      <pubDate>Fri, 01 May 2026 12:30:00 GMT</pubDate>
      <description>Technology and Innovation channel sample.</description>
      <category>Technology</category>
      <author>editor@example.test</author>
    </item>
  </channel>
</rss>
"""


def test_inman_rss_fixture_parses_items() -> None:
    """Inman recurring RSS discovery uses the generic kind=rss path."""
    response = FakeResponse(
        text=INMAN_RSS,
        url="https://feeds.feedburner.com/inmannews",
        headers={
            "Content-Type": "application/rss+xml; charset=UTF-8",
            "ETag": '"inman-fixture"',
            "Last-Modified": "Fri, 01 May 2026 13:00:00 GMT",
        },
    )
    with fake_request(response):
        result = rss_fetch.fetch_source(
            {
                "source_id": "inman_tech_innovation",
                "url": "https://feeds.feedburner.com/inmannews",
                "kind": "rss",
            }
        )

    assert result["source_id"] == "inman_tech_innovation"
    assert result["kind"] == "rss"
    assert result["soft_fail"] is None
    assert result["error"] is None
    assert result["http"]["status"] == 200
    assert result["http"]["content_type"].startswith("application/rss+xml")
    assert len(result["items"]) == 1
    assert result["items"][0]["id"] == "inman-tech-1"
    assert result["items"][0]["published"] == "2026-05-01T12:30:00Z"
    assert result["body"] is None


def test_http_static_html_returns_raw_body_and_metadata() -> None:
    """Static HTML discovery uses kind=http and keeps raw body plus HTTP metadata."""
    html = "<!doctype html><title>Example</title><main>Static article index</main>"
    response = FakeResponse(
        text=html,
        url="https://example.test/articles/",
        headers={"Content-Type": "text/html; charset=utf-8", "ETag": '"html-fixture"'},
    )
    with fake_request(response):
        result = rss_fetch.fetch_source(
            {
                "source_id": "example_html",
                "url": "https://example.test/articles/",
                "kind": "http",
            }
        )

    assert result["kind"] == "http"
    assert result["items"] == []
    assert result["body"] == html
    assert result["http"]["status"] == 200
    assert result["http"]["content_type"] == "text/html; charset=utf-8"
    assert result["http"]["final_url"] == "https://example.test/articles/"


def test_itunes_api_uses_http_path_without_separate_client() -> None:
    """iTunes lookup JSON is a regular kind=http fetch with raw JSON body."""
    body = '{"resultCount":1,"results":[{"trackName":"Zillow Real Estate & Rentals"}]}'
    response = FakeResponse(
        text=body,
        url="https://itunes.apple.com/lookup?id=310738695&country=us",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with fake_request(response):
        result = rss_fetch.fetch_source(
            {
                "source_id": "zillow_ios",
                "url": "https://itunes.apple.com/lookup?id=310738695&country=us",
                "kind": "http",
            }
        )

    assert result["kind"] == "http"
    assert result["items"] == []
    assert result["body"] == body
    assert result["http"]["content_type"] == "application/json; charset=utf-8"
    assert result["soft_fail"] is None


def test_soft_fail_labels_are_explicit() -> None:
    """Blocked, rate-limited, anti-bot, and timeout outcomes keep stable labels."""
    cases = [
        (
            FakeResponse(status_code=403, text="Subscribe to continue reading"),
            "blocked_or_paywall",
        ),
        (
            FakeResponse(status_code=429, text="Too many requests"),
            "rate_limited",
        ),
        (
            FakeResponse(status_code=200, text="Please complete this CAPTCHA"),
            "anti_bot",
        ),
        (
            requests.ReadTimeout("read timed out"),
            "timeout",
        ),
    ]

    for response_or_exc, expected in cases:
        with fake_request(response_or_exc):
            result = rss_fetch.fetch_source(
                {
                    "source_id": f"soft_fail_{expected}",
                    "url": "https://example.test/blocked",
                    "kind": "http",
                    "fetch_overrides": {"retries": 0, "timeout": [1, 1]},
                }
            )
        assert result["soft_fail"] == expected
        assert result["error"] is None


def test_batch_all_name_resolution_errors_classifies_environment_failure() -> None:
    """All fetchable sources failing DNS is a runner environment failure."""
    dns_error = requests.ConnectionError(
        NameResolutionError(
            "example.test",
            None,  # type: ignore[arg-type]
            socket.gaierror(-2, "Name or service not known"),
        )
    )
    specs = [
        {"source_id": "redfin_news", "url": "https://redfin.example/feed", "kind": "rss"},
        {"source_id": "costar_homes", "url": "https://costar.example/feed", "kind": "rss"},
    ]

    with fake_request(dns_error):
        doc = rss_fetch.fetch_batch(specs, fetched_at="2026-05-04T06:00:00Z")

    assert doc["batch_status"] == "environment_failure"
    assert doc["failure_class"] == "global_dns_resolution_failure"
    assert doc["run_failure"]["failure_type"] == "dns_resolution"
    assert doc["run_failure"]["affected_source_count"] == 2
    assert doc["run_failure"]["fetchable_source_count"] == 2
    assert [result["source_id"] for result in doc["results"]] == ["redfin_news", "costar_homes"]
    assert all(result["failure_class"] == "dns_resolution" for result in doc["results"])
    assert all(result["soft_fail"] is None for result in doc["results"])


def test_batch_single_timeout_remains_source_level_soft_fail() -> None:
    """One source timeout remains a source outcome, including costar_homes."""
    responses = {
        "https://costar.example/feed": requests.ReadTimeout("read timed out"),
        "https://redfin.example/feed": FakeResponse(
            text=INMAN_RSS,
            url="https://redfin.example/feed",
            headers={"Content-Type": "application/rss+xml"},
        ),
    }
    original = rss_fetch._do_request

    def _fake_do_request(url, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN202
        response_or_exc = responses[url]
        if isinstance(response_or_exc, Exception):
            raise response_or_exc
        return response_or_exc

    rss_fetch._do_request = _fake_do_request
    try:
        doc = rss_fetch.fetch_batch(
            [
                {"source_id": "costar_homes", "url": "https://costar.example/feed", "kind": "rss"},
                {"source_id": "redfin_news", "url": "https://redfin.example/feed", "kind": "rss"},
            ],
            fetched_at="2026-05-04T06:00:00Z",
        )
    finally:
        rss_fetch._do_request = original

    assert doc["batch_status"] == "partial_success"
    assert doc["failure_class"] is None
    assert doc["run_failure"] is None
    by_source = {result["source_id"]: result for result in doc["results"]}
    assert by_source["costar_homes"]["soft_fail"] == "timeout"
    assert by_source["costar_homes"]["failure_class"] == "timeout"
    assert by_source["redfin_news"]["soft_fail"] is None
    assert by_source["redfin_news"]["error"] is None


def test_batch_costar_timeout_does_not_mask_other_sources_dns_failure() -> None:
    """Known Costar timeout does not hide a resolver failure for the rest of the batch."""
    dns_error = requests.ConnectionError(
        NameResolutionError(
            "example.test",
            None,  # type: ignore[arg-type]
            socket.gaierror(-2, "Name or service not known"),
        )
    )
    responses = {
        "https://costar.example/feed": requests.ReadTimeout("read timed out"),
        "https://redfin.example/feed": dns_error,
        "https://zillow.example/feed": dns_error,
    }
    original = rss_fetch._do_request

    def _fake_do_request(url, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN202
        response_or_exc = responses[url]
        if isinstance(response_or_exc, Exception):
            raise response_or_exc
        return response_or_exc

    rss_fetch._do_request = _fake_do_request
    try:
        doc = rss_fetch.fetch_batch(
            [
                {"source_id": "costar_homes", "url": "https://costar.example/feed", "kind": "rss"},
                {"source_id": "redfin_news", "url": "https://redfin.example/feed", "kind": "rss"},
                {"source_id": "zillow_newsroom", "url": "https://zillow.example/feed", "kind": "rss"},
            ],
            fetched_at="2026-05-04T06:00:00Z",
        )
    finally:
        rss_fetch._do_request = original

    assert doc["batch_status"] == "environment_failure"
    assert doc["failure_class"] == "global_dns_resolution_failure"
    assert doc["run_failure"]["failure_type"] == "dns_resolution"
    assert doc["run_failure"]["affected_source_count"] == 2
    assert doc["run_failure"]["soft_failed_source_ids"] == ["costar_homes"]


def test_cli_multi_source_hard_failure_exits_nonzero() -> None:
    """A mixed batch with one hard source error exits nonzero with failed JSON."""
    responses = {
        "https://broken.example/feed": requests.ConnectionError("connection refused"),
        "https://inman.example/feed": FakeResponse(
            text=INMAN_RSS,
            url="https://inman.example/feed",
            headers={"Content-Type": "application/rss+xml"},
        ),
    }
    payload = {
        "sources": [
            {"source_id": "broken_source", "url": "https://broken.example/feed", "kind": "rss"},
            {"source_id": "inman_tech_innovation", "url": "https://inman.example/feed", "kind": "rss"},
        ]
    }

    original_request = rss_fetch._do_request
    original_argv = sys.argv
    original_stdin = sys.stdin

    def _fake_do_request(url, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN202
        response_or_exc = responses[url]
        if isinstance(response_or_exc, Exception):
            raise response_or_exc
        return response_or_exc

    stdout = io.StringIO()
    exit_code = 0
    rss_fetch._do_request = _fake_do_request
    sys.argv = ["rss_fetch.py", "--stdin"]
    sys.stdin = io.StringIO(json.dumps(payload))
    try:
        with redirect_stdout(stdout):
            try:
                rss_fetch.main()
            except SystemExit as exc:
                exit_code = int(exc.code)
    finally:
        rss_fetch._do_request = original_request
        sys.argv = original_argv
        sys.stdin = original_stdin

    doc = json.loads(stdout.getvalue())
    assert doc["batch_status"] == "failed"
    assert exit_code == 1


def test_cli_all_soft_failures_still_exit_10() -> None:
    """A batch where every source soft-fails keeps the documented exit 10."""
    payload = {
        "sources": [
            {"source_id": "blocked_one", "url": "https://blocked-one.example/feed", "kind": "rss"},
            {"source_id": "blocked_two", "url": "https://blocked-two.example/feed", "kind": "rss"},
        ]
    }

    original_request = rss_fetch._do_request
    original_argv = sys.argv
    original_stdin = sys.stdin

    def _fake_do_request(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        return FakeResponse(status_code=403, text="Subscribe to continue reading")

    stdout = io.StringIO()
    exit_code = 0
    rss_fetch._do_request = _fake_do_request
    sys.argv = ["rss_fetch.py", "--stdin"]
    sys.stdin = io.StringIO(json.dumps(payload))
    try:
        with redirect_stdout(stdout):
            try:
                rss_fetch.main()
            except SystemExit as exc:
                exit_code = int(exc.code)
    finally:
        rss_fetch._do_request = original_request
        sys.argv = original_argv
        sys.stdin = original_stdin

    doc = json.loads(stdout.getvalue())
    assert doc["batch_status"] == "soft_failed"
    assert exit_code == 10


def test_fetcher_does_not_write_state() -> None:
    """The fetcher returns JSON-ready data and leaves .state ownership to runtime."""
    response = FakeResponse(text="<html>ok</html>", headers={"Content-Type": "text/html"})
    original_cwd = pathlib.Path.cwd()
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        try:
            with fake_request(response):
                result = rss_fetch.fetch_source(
                    {
                        "source_id": "no_state",
                        "url": "https://example.test/no-state",
                        "kind": "http",
                    }
                )
            assert result["body"] == "<html>ok</html>"
            assert not (pathlib.Path(tmpdir) / ".state").exists()
        finally:
            os.chdir(original_cwd)


def main() -> None:
    tests = [
        test_inman_rss_fixture_parses_items,
        test_http_static_html_returns_raw_body_and_metadata,
        test_itunes_api_uses_http_path_without_separate_client,
        test_soft_fail_labels_are_explicit,
        test_batch_all_name_resolution_errors_classifies_environment_failure,
        test_batch_single_timeout_remains_source_level_soft_fail,
        test_batch_costar_timeout_does_not_mask_other_sources_dns_failure,
        test_cli_multi_source_hard_failure_exits_nonzero,
        test_cli_all_soft_failures_still_exit_10,
        test_fetcher_does_not_write_state,
    ]
    for test in tests:
        test()
        print(f"PASS  {test.__name__}")


if __name__ == "__main__":
    main()
