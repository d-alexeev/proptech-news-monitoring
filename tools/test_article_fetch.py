#!/usr/bin/env python3
"""
Offline contract tests for article_fetch.py.

Run with:
  python3 tools/test_article_fetch.py
"""
from __future__ import annotations

import io
import json
import pathlib
import sys
import tempfile
from contextlib import contextmanager
from contextlib import redirect_stdout
from typing import Iterator

import requests

import article_fetch


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
        self.headers = headers or {"Content-Type": "text/html; charset=utf-8"}


@contextmanager
def fake_request(response_or_exc: FakeResponse | Exception) -> Iterator[None]:
    original = article_fetch._do_request

    def _fake_do_request(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        if isinstance(response_or_exc, Exception):
            raise response_or_exc
        return response_or_exc

    article_fetch._do_request = _fake_do_request
    try:
        yield
    finally:
        article_fetch._do_request = original


ARTICLE_HTML = """<!doctype html>
<html>
  <head>
    <title>Portal launches verified seller tools</title>
    <script>ignoreMe()</script>
    <style>.hidden { display:none }</style>
  </head>
  <body>
    <nav>Navigation that should not dominate extraction</nav>
    <article>
      <h1>Portal launches verified seller tools</h1>
      <p>Real estate marketplace Example Portal launched verified seller tools for agents.</p>
      <p>The new workflow adds identity checks, listing quality prompts, and buyer messaging controls.</p>
      <p>Executives said the product is designed to reduce low-quality inventory and improve lead trust.</p>
      <p>Brokerage teams can review verification status inside their existing dashboard, compare seller
      records against listing submissions, and flag suspicious inventory before it reaches high-intent
      buyers. The company said the rollout is focused on public listing quality rather than private
      consumer profiling.</p>
      <p>Product managers also described a reporting layer that shows agents why a listing was delayed,
      which documents need correction, and whether the buyer messaging flow is active. Early pilots
      suggested that the checks reduced duplicate listings and shortened manual review queues.</p>
      <p>The marketplace plans to expand the controls across additional metropolitan areas after
      compliance review, with integrations for agency CRM tools and listing syndication partners.</p>
    </article>
    <footer>Footer noise</footer>
  </body>
</html>
"""

INMAN_PAYWALL_VISIBLE_TEXT_HTML = """<!doctype html>
<html>
  <body>
    <article>
      <h1>Real estate has an AI problem. This startup thinks it knows why</h1>
      <p>AI adoption in real estate is rising, but many agents are being left behind as complex tools limit real-world impact.</p>
      <p>When a real estate agent burned out, it was not because she lacked leads. It was because she had too many and no system to handle them.</p>
      <p>The experience became the foundation for a new entrant in the wave of all-in-one real estate super apps.</p>
      <p>The platform focuses on building business infrastructure first, then layering automation on top.</p>
    </article>
    <section class="subscribe-wall">
      <p>Subscribe to continue reading Inman Select.</p>
      <p>Log in or join Select to access exclusive industry content.</p>
    </section>
  </body>
</html>
"""


def article_spec(**overrides: object) -> dict:
    spec = {
        "source_id": "example_source",
        "url": "https://example.test/article",
        "canonical_url": "https://example.test/article",
        "title": "Portal launches verified seller tools",
        "published": "2026-05-04",
        "shortlist_run_id": "monitor_sources__20260504T120000Z__daily_core",
    }
    spec.update(overrides)
    return spec


def test_fetch_source_extracts_article_like_text_and_full_hint() -> None:
    with fake_request(FakeResponse(text=ARTICLE_HTML, url="https://example.test/article")):
        result = article_fetch.fetch_source(article_spec(), min_full_chars=120)

    assert result["source_id"] == "example_source"
    assert result["url"] == "https://example.test/article"
    assert result["canonical_url"] == "https://example.test/article"
    assert result["title"] == "Portal launches verified seller tools"
    assert result["published"] == "2026-05-04"
    assert result["body_status_hint"] == "full"
    assert result["fetch_method"] == "static_http"
    assert result["http"]["status"] == 200
    assert result["http"]["content_type"] == "text/html; charset=utf-8"
    assert "Real estate marketplace Example Portal" in result["text"]
    assert "ignoreMe" not in result["text"]
    assert "Footer noise" not in result["text"]
    assert result["text_char_count"] == len(result["text"])
    assert result["error"] is None
    assert result["soft_fail"] is None


def test_fetch_source_caps_extracted_text() -> None:
    html = "<article><p>" + ("Long body sentence. " * 200) + "</p></article>"
    with fake_request(FakeResponse(text=html)):
        result = article_fetch.fetch_source(article_spec(), max_chars=140, min_full_chars=80)

    assert result["body_status_hint"] == "full"
    assert result["text_char_count"] <= 140
    assert result["text"].endswith("...")


def test_fetch_source_uses_snippet_fallback_for_short_body() -> None:
    html = "<article><p>Short but useful snippet.</p></article>"
    with fake_request(FakeResponse(text=html)):
        result = article_fetch.fetch_source(article_spec(), min_full_chars=120)

    assert result["body_status_hint"] == "snippet_fallback"
    assert result["soft_fail"] is None
    assert result["failure_class"] == "below_minimum_body_threshold"
    assert result["text"] == "Short but useful snippet."


def test_fetch_source_classifies_blocked_and_rate_limited_responses() -> None:
    cases = [
        (FakeResponse(status_code=403, text="Forbidden"), "blocked_or_paywall"),
        (FakeResponse(status_code=429, text="Too many requests"), "rate_limited"),
        (FakeResponse(status_code=200, text="Please complete this CAPTCHA"), "anti_bot"),
    ]

    for response, expected in cases:
        with fake_request(response):
            result = article_fetch.fetch_source(article_spec())
        assert result["body_status_hint"] == "paywall_stub"
        assert result["soft_fail"] == expected
        assert result["failure_class"] == expected
        assert result["text"] == ""


def test_fetch_source_keeps_visible_inman_paywall_text_as_snippet_fallback() -> None:
    with fake_request(FakeResponse(text=INMAN_PAYWALL_VISIBLE_TEXT_HTML, url="https://www.inman.com/2026/05/01/example/")):
        result = article_fetch.fetch_source(
            article_spec(
                source_id="inman_tech_innovation",
                url="https://www.inman.com/2026/05/01/example/",
                canonical_url="https://www.inman.com/2026/05/01/example",
                title="Real estate has an AI problem. This startup thinks it knows why",
            ),
            min_full_chars=120,
        )

    assert result["body_status_hint"] == "snippet_fallback"
    assert result["soft_fail"] == "blocked_or_paywall"
    assert result["failure_class"] == "blocked_or_paywall"
    assert result["soft_fail_detail"] == "public_partial_text_extracted"
    assert "AI adoption in real estate is rising" in result["text"]
    assert "Subscribe to continue" not in result["text"]
    assert result["text_char_count"] == len(result["text"])


def test_fetch_source_uses_public_browser_fallback_for_inman_static_403() -> None:
    original_browser = article_fetch._fetch_inman_public_partial_with_browser

    def fake_browser(url: str, *, max_chars: int) -> dict | None:
        assert url == "https://www.inman.com/2026/05/01/example/"
        assert max_chars == article_fetch.DEFAULT_MAX_CHARS
        return {
            "status": 200,
            "elapsed_ms": 1200,
            "content_type": "text/html; charset=UTF-8",
            "final_url": "https://www.inman.com/2026/05/01/example/",
            "text": (
                "Browser-visible Inman article body with enough public text to analyze the story without login. "
                "Inman Events Promo block that should be removed. She pointed to a recent survey about AI adoption. "
                "Trending Related story block that should be removed. “Not because they’re unwilling,” she said. "
                "Show Comments Hide Comments Sign up for Inman newsletters Read Next Related story noise."
            ),
        }

    article_fetch._fetch_inman_public_partial_with_browser = fake_browser
    try:
        with fake_request(FakeResponse(status_code=403, text="Forbidden", url="https://www.inman.com/2026/05/01/example/")):
            result = article_fetch.fetch_source(
                article_spec(
                    source_id="inman_tech_innovation",
                    url="https://www.inman.com/2026/05/01/example/",
                    canonical_url="https://www.inman.com/2026/05/01/example",
                )
            )
    finally:
        article_fetch._fetch_inman_public_partial_with_browser = original_browser

    assert result["body_status_hint"] == "snippet_fallback"
    assert result["fetch_method"] == "browser_fallback"
    assert result["http"]["source"] == "browser_observation"
    assert result["soft_fail"] == "blocked_or_paywall"
    assert result["failure_class"] == "blocked_or_paywall"
    assert result["soft_fail_detail"] == "public_partial_text_extracted"
    assert "Browser-visible Inman article body" in result["text"]
    assert "She pointed to a recent survey" in result["text"]
    assert "Not because they" in result["text"]
    assert "Inman Events" not in result["text"]
    assert "Trending" not in result["text"]
    assert "Read Next" not in result["text"]


def test_fetch_source_classifies_timeout_as_snippet_fallback() -> None:
    with fake_request(requests.ReadTimeout("read timed out")):
        result = article_fetch.fetch_source(article_spec())

    assert result["body_status_hint"] == "snippet_fallback"
    assert result["soft_fail"] == "timeout"
    assert result["failure_class"] == "timeout"
    assert result["error"] is None


def test_fetch_batch_reports_mixed_status_counts() -> None:
    specs = [article_spec(source_id="one"), article_spec(source_id="two")]
    responses = iter(
        [
            FakeResponse(text=ARTICLE_HTML),
            FakeResponse(status_code=403, text="Forbidden"),
        ]
    )
    original = article_fetch._do_request

    def _fake_do_request(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        return next(responses)

    article_fetch._do_request = _fake_do_request
    try:
        doc = article_fetch.fetch_batch(specs, fetched_at="2026-05-04T12:00:00Z")
    finally:
        article_fetch._do_request = original

    assert doc["fetched_at"] == "2026-05-04T12:00:00Z"
    assert doc["batch_status"] == "partial_success"
    assert doc["summary_counts"] == {
        "full": 1,
        "snippet_fallback": 0,
        "paywall_stub": 1,
    }


def test_cli_stdin_emits_one_json_document() -> None:
    payload = {"articles": [article_spec()]}
    original_stdin = sys.stdin
    stdout = io.StringIO()
    try:
        sys.stdin = io.StringIO(json.dumps(payload))
        with fake_request(FakeResponse(text=ARTICLE_HTML)):
            with redirect_stdout(stdout):
                article_fetch.main(["--stdin"])
    finally:
        sys.stdin = original_stdin

    doc = json.loads(stdout.getvalue())
    assert doc["batch_status"] == "success"
    assert doc["results"][0]["body_status_hint"] == "full"


def test_article_fetch_does_not_write_state() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        with fake_request(FakeResponse(text=ARTICLE_HTML)):
            result = article_fetch.fetch_source(article_spec(), repo_root=root)

        assert result["body_status_hint"] == "full"
        assert not (root / ".state").exists()


def main() -> None:
    tests = [
        test_fetch_source_extracts_article_like_text_and_full_hint,
        test_fetch_source_caps_extracted_text,
        test_fetch_source_uses_snippet_fallback_for_short_body,
        test_fetch_source_classifies_blocked_and_rate_limited_responses,
        test_fetch_source_keeps_visible_inman_paywall_text_as_snippet_fallback,
        test_fetch_source_uses_public_browser_fallback_for_inman_static_403,
        test_fetch_source_classifies_timeout_as_snippet_fallback,
        test_fetch_batch_reports_mixed_status_counts,
        test_cli_stdin_emits_one_json_document,
        test_article_fetch_does_not_write_state,
    ]
    for test in tests:
        test()
    print(f"{len(tests)} tests passed")


if __name__ == "__main__":
    main()
