#!/usr/bin/env python3
"""
article_fetch.py — full-text fetch helper for explicitly shortlisted URLs.

This low-level helper emits one JSON document and writes no ./.state/ files.
It is intended for scrape_and_enrich inputs only, after a current-run shortlist
has already been emitted.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin

import requests


DEFAULT_USER_AGENT = "PropTechNewsMonitor/1.0 (+team@avito.example)"
DEFAULT_TIMEOUT = (10, 35)
DEFAULT_RETRIES = 1
DEFAULT_MAX_CHARS = 12000
DEFAULT_MIN_FULL_CHARS = 700
DEFAULT_MIN_PUBLIC_PARTIAL_CHARS = 120
PAYWALL_STUB_FAILS = {"blocked_or_paywall", "rate_limited", "anti_bot", "origin_blocked"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ArticleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._article_depth = 0
        self._main_depth = 0
        self.article_chunks: list[str] = []
        self.main_chunks: list[str] = []
        self.body_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg", "nav", "footer", "header", "aside"}:
            self._skip_depth += 1
        if tag == "article":
            self._article_depth += 1
        if tag == "main":
            self._main_depth += 1
        if tag in {"p", "h1", "h2", "h3", "li", "blockquote"}:
            self._append_break()

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"p", "h1", "h2", "h3", "li", "blockquote"}:
            self._append_break()
        if tag == "article" and self._article_depth:
            self._article_depth -= 1
        if tag == "main" and self._main_depth:
            self._main_depth -= 1
        if tag in {"script", "style", "noscript", "svg", "nav", "footer", "header", "aside"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = html.unescape(data or "").strip()
        if not text:
            return
        self.body_chunks.append(text)
        if self._main_depth:
            self.main_chunks.append(text)
        if self._article_depth:
            self.article_chunks.append(text)

    def _append_break(self) -> None:
        if self._skip_depth:
            return
        self.body_chunks.append("\n")
        if self._main_depth:
            self.main_chunks.append("\n")
        if self._article_depth:
            self.article_chunks.append("\n")

    def best_text(self) -> str:
        chunks = self.article_chunks or self.main_chunks or self.body_chunks
        return _compact_text(" ".join(chunks))


class LeadImageParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.og_image: str | None = None
        self.twitter_image: str | None = None
        self.image_src: str | None = None
        self.article_image: dict[str, Any] | None = None
        self.og_width: int | None = None
        self.og_height: int | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr = {key.lower(): value for key, value in attrs if key and value}
        if tag == "meta":
            prop = (attr.get("property") or attr.get("name") or "").lower()
            content = attr.get("content")
            if prop == "og:image" and content:
                self.og_image = content
            elif prop == "og:image:width":
                self.og_width = _safe_int(content)
            elif prop == "og:image:height":
                self.og_height = _safe_int(content)
            elif prop == "twitter:image" and content:
                self.twitter_image = content
        elif tag == "link" and (attr.get("rel") or "").lower() == "image_src" and attr.get("href"):
            self.image_src = attr["href"]
        elif tag == "img" and attr.get("src") and self.article_image is None:
            self.article_image = {
                "url": attr["src"],
                "alt": attr.get("alt"),
                "width": _safe_int(attr.get("width")),
                "height": _safe_int(attr.get("height")),
            }

    def best(self) -> dict[str, Any]:
        if self.og_image:
            return _available_lead_image(
                url=urljoin(self.base_url, self.og_image),
                source="og_image",
                width=self.og_width,
                height=self.og_height,
            )
        if self.twitter_image:
            return _available_lead_image(url=urljoin(self.base_url, self.twitter_image), source="twitter_image")
        if self.image_src:
            return _available_lead_image(url=urljoin(self.base_url, self.image_src), source="image_src")
        if self.article_image:
            return _available_lead_image(
                url=urljoin(self.base_url, str(self.article_image["url"])),
                source="article_image",
                alt=self.article_image.get("alt"),
                width=self.article_image.get("width"),
                height=self.article_image.get("height"),
            )
        return unavailable_lead_image()


def _safe_int(value: str | None) -> int | None:
    try:
        return int(str(value)) if value is not None and str(value).strip() else None
    except ValueError:
        return None


def unavailable_lead_image() -> dict[str, Any]:
    return {
        "status": "unavailable",
        "url": None,
        "source": "none",
        "alt": None,
        "content_type": None,
        "width": None,
        "height": None,
    }


def _available_lead_image(
    *,
    url: str,
    source: str,
    alt: str | None = None,
    width: int | None = None,
    height: int | None = None,
) -> dict[str, Any]:
    return {
        "status": "available",
        "url": url,
        "source": source,
        "alt": alt,
        "content_type": None,
        "width": width,
        "height": height,
    }


def _compact_text(text: str, *, max_chars: int | None = None) -> str:
    compact = re.sub(r"\s+", " ", text or "").strip()
    if max_chars is None or len(compact) <= max_chars:
        return compact
    if max_chars <= 3:
        return "." * max_chars
    return compact[: max_chars - 3].rstrip() + "..."


def _extract_article_text(body: str, *, max_chars: int) -> str:
    parser = ArticleTextParser()
    parser.feed(body or "")
    return _compact_text(parser.best_text(), max_chars=max_chars)


def _extract_lead_image(body: str, *, base_url: str) -> dict[str, Any]:
    parser = LeadImageParser(base_url)
    parser.feed(body or "")
    return parser.best()


def _classify_soft_fail(status: int | None, body_preview: str) -> tuple[str | None, str | None]:
    if status in (401, 402, 403, 451):
        return "blocked_or_paywall", f"http_{status}_observed"
    if status == 429:
        return "rate_limited", "http_429_observed"
    if status in (520, 521, 522, 523, 524):
        return "origin_blocked", f"http_{status}_observed"
    low = (body_preview or "").lower()[:4096]
    if "captcha" in low or "are you a human" in low or "verify you are human" in low:
        return "anti_bot", "captcha_or_human_check_visible"
    if "login required" in low or "sign in to continue" in low or "subscribe to continue" in low:
        return "blocked_or_paywall", "login_or_subscription_required"
    return None, None


def _is_inman_source(result: dict[str, Any]) -> bool:
    source_id = str(result.get("source_id") or "")
    url = str(result.get("url") or result.get("canonical_url") or "")
    return source_id == "inman_tech_innovation" or "://www.inman.com/" in url or "://inman.com/" in url


def _can_use_public_partial_text(result: dict[str, Any], *, status: int, soft_fail: str, text: str) -> bool:
    return (
        _is_inman_source(result)
        and status < 400
        and soft_fail == "blocked_or_paywall"
        and len(text) >= DEFAULT_MIN_PUBLIC_PARTIAL_CHARS
    )


def _trim_inman_public_partial_text(text: str) -> str:
    trimmed = text or ""
    for start, end in (
        ("Inman Events", "She pointed"),
        ("Trending", "“Not because"),
    ):
        start_idx = trimmed.find(start)
        end_idx = trimmed.find(end, start_idx + len(start)) if start_idx >= 0 else -1
        if start_idx >= 0 and end_idx > start_idx:
            trimmed = trimmed[:start_idx] + trimmed[end_idx:]
    for marker in (
        "Show Comments",
        "Sign up for Inman",
        "Read Next",
        "More in AI",
        "Read next",
    ):
        idx = trimmed.find(marker)
        if idx > 0:
            trimmed = trimmed[:idx]
    return _compact_text(trimmed)


def _fetch_inman_public_partial_with_browser(url: str, *, max_chars: int) -> dict[str, Any] | None:
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except Exception:  # noqa: BLE001
        return None

    started = time.monotonic()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            )
            response = page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            try:
                page.wait_for_load_state("networkidle", timeout=10_000)
            except PlaywrightTimeoutError:
                pass
            body = page.content()
            final_url = page.url
            status = response.status if response else None
            content_type = response.headers.get("content-type") if response else None
            browser.close()
    except (PlaywrightError, PlaywrightTimeoutError):
        return None

    if status is None or status >= 400:
        return None

    text = _trim_inman_public_partial_text(_extract_article_text(body, max_chars=max_chars))
    if len(text) < DEFAULT_MIN_PUBLIC_PARTIAL_CHARS:
        return None

    return {
        "status": status,
        "elapsed_ms": int((time.monotonic() - started) * 1000),
        "content_type": content_type,
        "final_url": final_url,
        "text": text,
    }


def _apply_public_partial_text(
    result: dict[str, Any],
    *,
    text: str,
    http: dict[str, Any],
    fetch_method: str,
) -> dict[str, Any]:
    result["body_status_hint"] = "snippet_fallback"
    result["fetch_method"] = fetch_method
    result["http"] = http
    clean_text = _trim_inman_public_partial_text(text) if _is_inman_source(result) else text
    result["text"] = clean_text
    result["text_char_count"] = len(clean_text)
    result["failure_class"] = "blocked_or_paywall"
    result["soft_fail"] = "blocked_or_paywall"
    result["soft_fail_detail"] = "public_partial_text_extracted"
    return result


def _do_request(url: str, *, timeout: tuple[int, int] = DEFAULT_TIMEOUT, retries: int = DEFAULT_RETRIES) -> requests.Response:
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.7",
        "Accept-Language": "en;q=0.9,ru;q=0.7",
    }
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        except (requests.ConnectTimeout, requests.ReadTimeout) as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(1.0 * (attempt + 1))
            else:
                raise
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(1.0 * (attempt + 1))
            else:
                raise
    raise last_exc  # type: ignore[misc]


def _base_result(spec: dict) -> dict[str, Any]:
    return {
        "source_id": spec.get("source_id") or "",
        "url": spec.get("url") or "",
        "canonical_url": spec.get("canonical_url") or spec.get("url") or "",
        "title": spec.get("title") or "",
        "published": spec.get("published"),
        "shortlist_run_id": spec.get("shortlist_run_id"),
        "fetch_method": "static_http",
        "http": None,
        "body_status_hint": "snippet_fallback",
        "lead_image": unavailable_lead_image(),
        "text": "",
        "text_char_count": 0,
        "error": None,
        "failure_class": None,
        "soft_fail": None,
        "soft_fail_detail": None,
    }


def fetch_source(
    spec: dict,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    min_full_chars: int = DEFAULT_MIN_FULL_CHARS,
    repo_root: Path | None = None,
) -> dict:
    del repo_root  # The helper must not write state; kept for no-write tests.
    result = _base_result(spec)
    url = result["url"]
    if not url:
        result["error"] = "missing url"
        result["failure_class"] = "invalid_article_spec"
        return result

    started = time.monotonic()
    try:
        response = _do_request(url)
    except (requests.ConnectTimeout, requests.ReadTimeout) as exc:
        result["failure_class"] = "timeout"
        result["soft_fail"] = "timeout"
        result["soft_fail_detail"] = f"{exc.__class__.__name__}: {exc}"
        return result
    except Exception as exc:  # noqa: BLE001
        result["error"] = f"network_error: {exc.__class__.__name__}: {exc}"
        result["failure_class"] = "network_error"
        return result

    elapsed_ms = int((time.monotonic() - started) * 1000)
    body = response.text or ""
    status = response.status_code
    result["lead_image"] = _extract_lead_image(body, base_url=response.url or url)
    result["http"] = {
        "status": status,
        "elapsed_ms": elapsed_ms,
        "content_type": response.headers.get("Content-Type"),
        "final_url": response.url,
    }

    soft_fail, soft_fail_detail = _classify_soft_fail(status, body)
    extracted = _extract_article_text(body, max_chars=max_chars) if status < 400 else ""
    if soft_fail:
        if _can_use_public_partial_text(result, status=status, soft_fail=soft_fail, text=extracted):
            return _apply_public_partial_text(
                result,
                text=extracted,
                http=result["http"],
                fetch_method="static_http",
            )
        if _is_inman_source(result) and soft_fail == "blocked_or_paywall":
            observed = _fetch_inman_public_partial_with_browser(url, max_chars=max_chars)
            if observed:
                return _apply_public_partial_text(
                    result,
                    text=observed["text"],
                    http={
                        "status": observed["status"],
                        "elapsed_ms": observed["elapsed_ms"],
                        "content_type": observed["content_type"],
                        "final_url": observed["final_url"],
                        "source": "browser_observation",
                    },
                    fetch_method="browser_fallback",
                )
        result["body_status_hint"] = "paywall_stub" if soft_fail in PAYWALL_STUB_FAILS else "snippet_fallback"
        result["failure_class"] = soft_fail
        result["soft_fail"] = soft_fail
        result["soft_fail_detail"] = soft_fail_detail
        return result

    if status >= 400:
        result["error"] = f"http_error: {status}"
        result["failure_class"] = "http_error"
        return result

    result["text"] = extracted
    result["text_char_count"] = len(extracted)
    if len(extracted) >= min_full_chars:
        result["body_status_hint"] = "full"
    else:
        result["body_status_hint"] = "snippet_fallback"
        result["failure_class"] = "below_minimum_body_threshold"
    return result


def _batch_status(results: list[dict]) -> tuple[str, str | None, dict | None]:
    if not results:
        return "success", None, None
    if all(result.get("body_status_hint") == "paywall_stub" for result in results):
        return "soft_failed", None, None
    if any(result.get("error") and not result.get("soft_fail") for result in results):
        return "failed", None, None
    if any(result.get("body_status_hint") != "full" for result in results):
        return "partial_success", None, None
    return "success", None, None


def _summary_counts(results: list[dict]) -> dict[str, int]:
    return {
        "full": sum(1 for result in results if result.get("body_status_hint") == "full"),
        "snippet_fallback": sum(
            1 for result in results if result.get("body_status_hint") == "snippet_fallback"
        ),
        "paywall_stub": sum(
            1 for result in results if result.get("body_status_hint") == "paywall_stub"
        ),
    }


def fetch_batch(specs: list[dict], *, fetched_at: str | None = None) -> dict:
    results = [fetch_source(spec) for spec in specs]
    status, failure_class, run_failure = _batch_status(results)
    return {
        "fetched_at": fetched_at or _now_iso(),
        "results": results,
        "batch_status": status,
        "failure_class": failure_class,
        "run_failure": run_failure,
        "summary_counts": _summary_counts(results),
    }


def _parse_cli(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch article text for shortlisted URLs")
    parser.add_argument("--stdin", action="store_true", help="Read batch JSON {articles:[...]} from stdin")
    parser.add_argument("--pretty", action="store_true", help="Indent stdout JSON")
    parser.add_argument("--source-id")
    parser.add_argument("--url")
    parser.add_argument("--canonical-url")
    parser.add_argument("--title")
    parser.add_argument("--published")
    parser.add_argument("--shortlist-run-id")
    return parser.parse_args(argv)


def _iter_specs(args: argparse.Namespace) -> Iterable[dict]:
    if args.stdin:
        raw = sys.stdin.read()
        if not raw.strip():
            return []
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            print(f"stdin is not valid JSON: {exc}", file=sys.stderr)
            sys.exit(2)
        articles = payload.get("articles")
        if not isinstance(articles, list):
            print("stdin JSON must have top-level 'articles' array", file=sys.stderr)
            sys.exit(2)
        return articles
    if not args.url:
        print("either --stdin or --url is required", file=sys.stderr)
        sys.exit(2)
    return [
        {
            "source_id": args.source_id or "",
            "url": args.url,
            "canonical_url": args.canonical_url or args.url,
            "title": args.title or "",
            "published": args.published,
            "shortlist_run_id": args.shortlist_run_id,
        }
    ]


def main(argv: list[str] | None = None) -> None:
    args = _parse_cli(argv)
    doc = fetch_batch(list(_iter_specs(args)))
    indent = 2 if args.pretty else None
    sys.stdout.write(json.dumps(doc, ensure_ascii=False, indent=indent))
    sys.stdout.write("\n")

    if doc.get("batch_status") == "failed":
        sys.exit(1)
    if doc.get("batch_status") == "soft_failed":
        sys.exit(10)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"unhandled_error: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
