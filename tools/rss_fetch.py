#!/usr/bin/env python3
"""
rss_fetch.py — HTTP/RSS fetcher for PropTech News Monitoring.

Fetches raw content for sources with fetch_strategy in {rss, html_scrape}.
Emits a single JSON document on stdout with parsed feed items (for RSS/Atom)
or raw body (for plain HTTP). Does not write to ./.state/.

Two input modes:

  CLI single-source:
    python3 tools/rss_fetch.py \
        --source-id redfin_news \
        --url https://www.redfin.com/news/feed/ \
        [--kind rss|http]

  Batch via stdin (JSON):
    echo '{"sources":[{"source_id":"redfin_news","url":"...","kind":"rss"}]}' \
        | python3 tools/rss_fetch.py --stdin

Output (stdout, one JSON document):

  {
    "fetched_at": "2026-04-21T10:42:03Z",
    "results": [
      {
        "source_id": "redfin_news",
        "url": "...",
        "kind": "rss",
        "http": {"status": 200, "elapsed_ms": 412, "etag": "...", "last_modified": "..."},
        "items": [                   # only for kind=rss
          {
            "id": "...",
            "title": "...",
            "link": "...",
            "published": "2026-04-20T12:00:00Z",
            "summary": "...",
            "authors": ["..."],
            "tags": ["..."]
          }
        ],
        "body": null,                # only for kind=http: raw text
        "error": null,
        "soft_fail": null            # "blocked" | "paywall" | ... when status says so
      }
    ]
  }

Exit codes:
  0  all sources fetched (items may be empty, soft_fail may be set)
  1  unexpected error (network stack, parser crash)
  2  invalid arguments
  10 every source soft-failed (blocked/anti-bot/paywall) — caller should emit change_request
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Iterable

import requests
import feedparser
from dateutil import parser as date_parser


DEFAULT_USER_AGENT = os.environ.get(
    "HTTP_USER_AGENT",
    "PropTechNewsMonitor/1.0 (+team@avito.example)",
)
DEFAULT_TIMEOUT = (10, 45)  # (connect, read) seconds
DEFAULT_RETRIES = 2
# Per-host overrides for flaky sources. Each entry may override timeout
# (connect, read), retries count, and backoff base. The host_key is a substring
# matched against the URL.
#
# investors.costargroup.com: server is often slow to first byte but hangs fast
# past read timeout. Keep read budget modest and give up quickly with 1 retry,
# so the runner can move on to other sources and fetch costar in isolation on
# the next run. The outcome is soft_fail="timeout" rather than a hard failure.
PER_HOST_OVERRIDES: dict[str, dict] = {
    "investors.costargroup.com": {"timeout": (10, 20), "retries": 1, "backoff": 2.0},
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_published(raw: Any) -> str | None:
    if not raw:
        return None
    if isinstance(raw, time.struct_time):
        try:
            return datetime(*raw[:6], tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except (TypeError, ValueError):
            return None
    if isinstance(raw, str):
        try:
            dt = date_parser.parse(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except (ValueError, TypeError):
            return None
    return None


def _classify_soft_fail(status: int, body_preview: str) -> str | None:
    """Return a soft-fail label if the response looks like blocked/paywall/anti-bot."""
    if status in (401, 402, 403, 451):
        return "blocked_or_paywall"
    if status == 429:
        return "rate_limited"
    if status in (520, 521, 522, 523, 524):  # Cloudflare family
        return "origin_blocked"
    low = body_preview.lower()[:2048]
    if "captcha" in low or "access denied" in low or "are you a human" in low:
        return "anti_bot"
    return None


def _resolve_fetch_params(
    url: str,
    spec_overrides: dict | None = None,
) -> tuple[tuple[int, int], int, float]:
    """Return (timeout, retries, backoff_base) for a given URL.

    Precedence: per-spec overrides > PER_HOST_OVERRIDES > module defaults.
    """
    timeout: tuple[int, int] = DEFAULT_TIMEOUT
    retries = DEFAULT_RETRIES
    backoff = 1.5
    for host_key, cfg in PER_HOST_OVERRIDES.items():
        if host_key in url:
            timeout = tuple(cfg.get("timeout", timeout))  # type: ignore[assignment]
            retries = int(cfg.get("retries", retries))
            backoff = float(cfg.get("backoff", backoff))
            break
    if spec_overrides:
        if spec_overrides.get("timeout"):
            timeout = tuple(spec_overrides["timeout"])  # type: ignore[assignment]
        if spec_overrides.get("retries") is not None:
            retries = int(spec_overrides["retries"])
        if spec_overrides.get("backoff") is not None:
            backoff = float(spec_overrides["backoff"])
    return timeout, retries, backoff


def _do_request(
    url: str,
    extra_headers: dict | None = None,
    *,
    timeout: tuple[int, int] | None = None,
    retries: int | None = None,
    backoff: float = 1.5,
) -> requests.Response:
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, text/html;q=0.8, */*;q=0.5",
        "Accept-Language": "en;q=0.9, ru;q=0.7",
    }
    if extra_headers:
        headers.update(extra_headers)

    to = timeout or DEFAULT_TIMEOUT
    r = DEFAULT_RETRIES if retries is None else retries

    last_exc: Exception | None = None
    for attempt in range(r + 1):
        try:
            resp = requests.get(
                url,
                headers=headers,
                timeout=to,
                allow_redirects=True,
            )
            return resp
        except (requests.ConnectTimeout, requests.ReadTimeout) as exc:
            # Timeout — these are the main cause of flaky batch failures; wait longer.
            last_exc = exc
            if attempt < r:
                time.sleep(backoff * (attempt + 1) * 2)
            else:
                raise
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < r:
                time.sleep(backoff * (attempt + 1))
            else:
                raise
    # unreachable
    raise last_exc  # type: ignore[misc]


def fetch_source(spec: dict) -> dict:
    """Fetch one source spec. Returns a result dict (never raises for soft fails)."""
    source_id = spec.get("source_id") or ""
    url = spec.get("url") or ""
    kind = (spec.get("kind") or "rss").lower()
    if not url:
        return {
            "source_id": source_id,
            "url": url,
            "kind": kind,
            "http": None,
            "items": [],
            "body": None,
            "error": "missing url",
            "soft_fail": None,
        }
    if kind not in ("rss", "http"):
        return {
            "source_id": source_id,
            "url": url,
            "kind": kind,
            "http": None,
            "items": [],
            "body": None,
            "error": f"unsupported kind: {kind}",
            "soft_fail": None,
        }

    extra_headers: dict = {}
    if spec.get("etag"):
        extra_headers["If-None-Match"] = spec["etag"]
    if spec.get("last_modified"):
        extra_headers["If-Modified-Since"] = spec["last_modified"]

    timeout, retries, backoff = _resolve_fetch_params(url, spec.get("fetch_overrides"))
    started = time.monotonic()
    try:
        resp = _do_request(
            url,
            extra_headers=extra_headers or None,
            timeout=timeout,
            retries=retries,
            backoff=backoff,
        )
    except (requests.ConnectTimeout, requests.ReadTimeout) as exc:
        # Timeout → soft_fail. Downstream should retry next run, not emit a CR.
        return {
            "source_id": source_id,
            "url": url,
            "kind": kind,
            "http": None,
            "items": [],
            "body": None,
            "error": None,
            "soft_fail": "timeout",
            "soft_fail_detail": f"{exc.__class__.__name__}: {exc}",
        }
    except Exception as exc:  # noqa: BLE001 — surface as error string
        return {
            "source_id": source_id,
            "url": url,
            "kind": kind,
            "http": None,
            "items": [],
            "body": None,
            "error": f"network_error: {exc.__class__.__name__}: {exc}",
            "soft_fail": None,
        }
    elapsed_ms = int((time.monotonic() - started) * 1000)

    status = resp.status_code
    http_meta = {
        "status": status,
        "elapsed_ms": elapsed_ms,
        "etag": resp.headers.get("ETag"),
        "last_modified": resp.headers.get("Last-Modified"),
        "content_type": resp.headers.get("Content-Type"),
        "final_url": resp.url,
    }

    if status == 304:
        return {
            "source_id": source_id,
            "url": url,
            "kind": kind,
            "http": http_meta,
            "items": [],
            "body": None,
            "error": None,
            "soft_fail": None,
            "not_modified": True,
        }

    body_text = resp.text or ""
    soft = _classify_soft_fail(status, body_text)

    if soft:
        return {
            "source_id": source_id,
            "url": url,
            "kind": kind,
            "http": http_meta,
            "items": [],
            "body": body_text[:2000] if kind == "http" else None,
            "error": None,
            "soft_fail": soft,
        }

    if status >= 400:
        return {
            "source_id": source_id,
            "url": url,
            "kind": kind,
            "http": http_meta,
            "items": [],
            "body": None,
            "error": f"http_error: {status}",
            "soft_fail": None,
        }

    if kind == "http":
        return {
            "source_id": source_id,
            "url": url,
            "kind": kind,
            "http": http_meta,
            "items": [],
            "body": body_text,
            "error": None,
            "soft_fail": None,
        }

    # kind == rss
    parsed = feedparser.parse(body_text)
    bozo = bool(getattr(parsed, "bozo", False))
    bozo_exc = str(getattr(parsed, "bozo_exception", "")) if bozo else None

    items: list[dict] = []
    for entry in parsed.entries or []:
        link = entry.get("link") or ""
        if not link and entry.get("links"):
            for lnk in entry["links"]:
                if lnk.get("rel") in (None, "alternate") and lnk.get("href"):
                    link = lnk["href"]
                    break
        published = _normalize_published(
            entry.get("published")
            or entry.get("updated")
            or entry.get("published_parsed")
            or entry.get("updated_parsed")
        )
        authors = []
        if entry.get("authors"):
            authors = [a.get("name", "") for a in entry["authors"] if a.get("name")]
        elif entry.get("author"):
            authors = [entry["author"]]
        tags = []
        if entry.get("tags"):
            tags = [t.get("term", "") for t in entry["tags"] if t.get("term")]

        items.append({
            "id": entry.get("id") or entry.get("guid") or link,
            "title": (entry.get("title") or "").strip(),
            "link": link,
            "published": published,
            "summary": (entry.get("summary") or "").strip(),
            "authors": authors,
            "tags": tags,
        })

    result: dict[str, Any] = {
        "source_id": source_id,
        "url": url,
        "kind": kind,
        "http": http_meta,
        "items": items,
        "body": None,
        "error": None,
        "soft_fail": None,
    }
    if bozo and not items:
        result["error"] = f"feed_parse_error: {bozo_exc}"
    elif bozo:
        result["warning"] = f"feed_parse_warning: {bozo_exc}"
    return result


def _parse_cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PropTech RSS/HTTP fetcher")
    p.add_argument("--source-id", help="Source id from config/runtime/source-groups/*.yaml")
    p.add_argument("--url", help="Feed or page URL")
    p.add_argument("--kind", choices=("rss", "http"), default="rss")
    p.add_argument("--stdin", action="store_true", help="Read a batch JSON {sources:[...]} from stdin")
    p.add_argument("--pretty", action="store_true", help="Indent stdout JSON")
    return p.parse_args()


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
        print("either --stdin or (--url [--source-id] [--kind]) is required", file=sys.stderr)
        sys.exit(2)
    return [{"source_id": args.source_id or "", "url": args.url, "kind": args.kind}]


def main() -> None:
    args = _parse_cli()
    specs = list(_iter_specs(args))
    results = [fetch_source(spec) for spec in specs]

    doc = {
        "fetched_at": _now_iso(),
        "results": results,
    }

    indent = 2 if args.pretty else None
    sys.stdout.write(json.dumps(doc, ensure_ascii=False, indent=indent))
    sys.stdout.write("\n")

    if results and all(r.get("soft_fail") for r in results):
        sys.exit(10)
    if any(r.get("error") and not r.get("soft_fail") for r in results) and len(results) == 1:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"unhandled_error: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
