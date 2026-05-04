#!/usr/bin/env python3
"""
browser_fetch.py — headless browser fetcher for configured chrome_scrape sources.

This helper is a low-level JSON-in/JSON-out runner tool. It does not write
./.state/ and does not decide shortlist, digest, or enrichment outcomes.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from typing import Any, Callable, Iterable


DEFAULT_MAX_TEXT_CHARS = 6000
DEFAULT_TIMEOUT_MS = 30_000


class BrowserRuntimeUnavailable(RuntimeError):
    """Raised when Playwright or its browser runtime is unavailable."""


BrowserRunner = Callable[[dict], dict]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _compact_text(text: str, *, max_chars: int = DEFAULT_MAX_TEXT_CHARS) -> str:
    compact = re.sub(r"\s+", " ", text or "").strip()
    if len(compact) <= max_chars:
        return compact
    if max_chars <= 3:
        return "." * max_chars
    return compact[: max_chars - 3].rstrip() + "..."


def _classify_soft_fail(status_like: int | None, text: str) -> tuple[str | None, str | None]:
    if status_like in (401, 402, 403, 451):
        return "blocked_or_paywall", f"http_{status_like}_observed"
    if status_like == 429:
        return "rate_limited", "http_429_observed"
    if status_like in (520, 521, 522, 523, 524):
        return "origin_blocked", f"http_{status_like}_observed"
    low = (text or "").lower()[:4096]
    if "captcha" in low or "are you a human" in low or "verify you are human" in low:
        return "anti_bot", "captcha_or_human_check_visible"
    if "login required" in low or "sign in to continue" in low:
        return "blocked_or_paywall", "login_required"
    return None, None


def default_browser_runner(spec: dict) -> dict:
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # noqa: BLE001
        raise BrowserRuntimeUnavailable(f"{exc.__class__.__name__}: {exc}") from exc

    url = str(spec.get("url") or "")
    timeout_ms = int(spec.get("browser_timeout_ms") or DEFAULT_TIMEOUT_MS)
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
            response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            try:
                page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 10_000))
            except PlaywrightTimeoutError:
                pass
            text = page.locator("body").inner_text(timeout=5_000)
            final_url = page.url
            status_like = response.status if response else None
            content_type = None
            if response:
                content_type = response.headers.get("content-type")
            browser.close()
    except PlaywrightTimeoutError as exc:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        return {
            "status_like": None,
            "content_type": None,
            "final_url": url,
            "elapsed_ms": elapsed_ms,
            "text": "",
            "html": None,
            "soft_fail": "timeout",
            "soft_fail_detail": f"{exc.__class__.__name__}: {exc}",
        }
    except PlaywrightError as exc:
        raise BrowserRuntimeUnavailable(f"{exc.__class__.__name__}: {exc}") from exc

    elapsed_ms = int((time.monotonic() - started) * 1000)
    return {
        "status_like": status_like,
        "content_type": content_type,
        "final_url": final_url,
        "elapsed_ms": elapsed_ms,
        "text": text,
        "html": None,
    }


DEFAULT_BROWSER_RUNNER: BrowserRunner = default_browser_runner


def _base_result(spec: dict) -> dict[str, Any]:
    return {
        "source_id": spec.get("source_id") or "",
        "source_group": spec.get("source_group"),
        "url": spec.get("url") or "",
        "kind": "browser",
        "http": None,
        "final_url": spec.get("url") or "",
        "elapsed_ms": None,
        "text": "",
        "html": None,
        "items": [],
        "error": None,
        "failure_class": None,
        "soft_fail": None,
        "soft_fail_detail": None,
        "browser": {
            "interface": "playwright",
            "mode": "headless",
            "headless": True,
            "user_agent_family": "chrome",
            "network_events_available": False,
        },
    }


def fetch_source(
    spec: dict,
    *,
    browser_runner: BrowserRunner | None = None,
    max_text_chars: int = DEFAULT_MAX_TEXT_CHARS,
) -> dict:
    result = _base_result(spec)
    strategy = spec.get("fetch_strategy")
    if strategy != "chrome_scrape":
        result["error"] = f"unsupported fetch_strategy: {strategy}"
        result["failure_class"] = "invalid_source_spec"
        return result
    if not spec.get("url"):
        result["error"] = "missing url"
        result["failure_class"] = "invalid_source_spec"
        return result

    runner = browser_runner or DEFAULT_BROWSER_RUNNER
    try:
        observed = runner(spec)
    except BrowserRuntimeUnavailable as exc:
        result["error"] = f"browser_runtime_unavailable: {exc}"
        result["failure_class"] = "browser_runtime_unavailable"
        return result
    except Exception as exc:  # noqa: BLE001
        result["error"] = f"browser_error: {exc.__class__.__name__}: {exc}"
        result["failure_class"] = "browser_error"
        return result

    status_like = observed.get("status_like")
    text = _compact_text(str(observed.get("text") or ""), max_chars=max_text_chars)
    soft_fail = observed.get("soft_fail")
    soft_fail_detail = observed.get("soft_fail_detail")
    if not soft_fail:
        soft_fail, soft_fail_detail = _classify_soft_fail(status_like, text)

    result.update(
        {
            "http": {
                "status_like": status_like,
                "content_type": observed.get("content_type"),
                "source": "browser_observation",
            },
            "final_url": observed.get("final_url") or result["url"],
            "elapsed_ms": observed.get("elapsed_ms"),
            "text": text,
            "html": observed.get("html"),
            "failure_class": soft_fail,
            "soft_fail": soft_fail,
            "soft_fail_detail": soft_fail_detail,
        }
    )
    return result


def _batch_status(results: list[dict]) -> tuple[str, str | None, dict | None]:
    if results and all(result.get("failure_class") == "browser_runtime_unavailable" for result in results):
        return (
            "environment_failure",
            "browser_runtime_unavailable",
            {
                "failure_type": "browser_runtime_unavailable",
                "message": "Playwright or its Chromium runtime is unavailable in the runner environment.",
                "affected_source_count": len(results),
                "source_ids": [result.get("source_id") for result in results],
            },
        )
    if any(result.get("error") and not result.get("soft_fail") for result in results):
        return "failed", None, None
    if results and all(result.get("soft_fail") for result in results):
        return "soft_failed", None, None
    if any(result.get("soft_fail") for result in results):
        return "partial_success", None, None
    return "success", None, None


def fetch_batch(
    specs: list[dict],
    *,
    fetched_at: str | None = None,
    browser_runner: BrowserRunner | None = None,
) -> dict:
    results = [fetch_source(spec, browser_runner=browser_runner) for spec in specs]
    status, failure_class, run_failure = _batch_status(results)
    return {
        "fetched_at": fetched_at or _now_iso(),
        "results": results,
        "batch_status": status,
        "failure_class": failure_class,
        "run_failure": run_failure,
    }


def _parse_cli(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PropTech headless browser fetcher")
    parser.add_argument("--source-id", help="Source id from config/runtime/source-groups/*.yaml")
    parser.add_argument("--source-group", help="Source group id")
    parser.add_argument("--url", help="Public page URL")
    parser.add_argument("--fetch-strategy", default="chrome_scrape")
    parser.add_argument("--stdin", action="store_true", help="Read a batch JSON {sources:[...]} from stdin")
    parser.add_argument("--pretty", action="store_true", help="Indent stdout JSON")
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
        sources = payload.get("sources")
        if not isinstance(sources, list):
            print("stdin JSON must have top-level 'sources' array", file=sys.stderr)
            sys.exit(2)
        return sources
    if not args.url:
        print("either --stdin or (--url [--source-id] [--source-group]) is required", file=sys.stderr)
        sys.exit(2)
    return [
        {
            "source_id": args.source_id or "",
            "source_group": args.source_group,
            "fetch_strategy": args.fetch_strategy,
            "url": args.url,
        }
    ]


def main(argv: list[str] | None = None) -> None:
    args = _parse_cli(argv)
    specs = list(_iter_specs(args))
    doc = fetch_batch(specs)
    indent = 2 if args.pretty else None
    sys.stdout.write(json.dumps(doc, ensure_ascii=False, indent=indent))
    sys.stdout.write("\n")

    if doc.get("batch_status") == "environment_failure":
        sys.exit(1)
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
