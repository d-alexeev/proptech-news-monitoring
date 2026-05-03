#!/usr/bin/env python3
"""
Offline contract tests for rss_fetch.py.

Run with:
  python3 tools/test_rss_fetch.py
"""
from __future__ import annotations

import os
import pathlib
import tempfile
import warnings
from contextlib import contextmanager
from typing import Iterator

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL.*")

import requests

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
        test_fetcher_does_not_write_state,
    ]
    for test in tests:
        test()
        print(f"PASS  {test.__name__}")


if __name__ == "__main__":
    main()
