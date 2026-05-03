#!/usr/bin/env python3
"""
pdf_extract.py — enrichment-only PDF text helper for PropTech News Monitoring.

Extracts compact text and metadata from a local public PDF path or a public PDF
URL passed by the runner. This helper is intended only for shortlisted
scrape_and_enrich inputs such as Rightmove RNS PDFs. It does not write ./.state/.

Single-source examples:

  python3 tools/pdf_extract.py --source-id rightmove_plc_rns --path ./rns.pdf

  python3 tools/pdf_extract.py \
      --source-id rightmove_plc_rns \
      --url https://example.test/rightmove-rns.pdf

Batch via stdin:

  echo '{"sources":[{"source_id":"rightmove_plc_rns","url":"https://...pdf"}]}' \
      | python3 tools/pdf_extract.py --stdin
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - exercised when dependency is absent
    PdfReader = None  # type: ignore[assignment]


DEFAULT_USER_AGENT = os.environ.get(
    "HTTP_USER_AGENT",
    "PropTechNewsMonitor/1.0 (+team@avito.example)",
)
DEFAULT_TIMEOUT = (10, 45)
DEFAULT_MAX_CHARS = 12000
DEFAULT_MIN_TEXT_CHARS = 80
DEFAULT_MAX_BYTES = 5_000_000
DEFAULT_MAX_PAGES = 8
DOWNLOAD_CHUNK_SIZE = 64 * 1024


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _empty_result(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": spec.get("source_id") or "",
        "url": spec.get("url"),
        "path": spec.get("path"),
        "kind": "pdf",
        "metadata": {
            "page_count": None,
            "title": None,
            "author": None,
        },
        "text": "",
        "text_char_count": 0,
        "error": None,
        "soft_fail": None,
        "body_status_hint": "snippet_fallback",
    }


def _normalize_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        cleaned = re.sub(r"\s+", " ", line).strip()
        if cleaned:
            lines.append(cleaned)
    return "\n".join(lines)


def _normalize_text_limited(text: str, max_chars: int) -> tuple[str, int]:
    """Normalize text while storing at most max_chars.

    Returns (stored_text, observed_normalized_chars). The observed count can
    exceed max_chars, but the returned text never does.
    """
    if max_chars <= 0:
        return "", 0
    chars: list[str] = []
    stored = 0
    observed = 0
    pending_space = False
    for char in text:
        if char.isspace():
            if observed > 0:
                pending_space = True
            continue
        if pending_space:
            observed += 1
            if stored < max_chars:
                chars.append(" ")
                stored += 1
            pending_space = False
        observed += 1
        if stored < max_chars:
            chars.append(char)
            stored += 1
    return "".join(chars), observed


def _metadata_value(metadata: Any, key: str) -> str | None:
    if not metadata:
        return None
    raw = None
    try:
        raw = metadata.get(key)
    except AttributeError:
        raw = getattr(metadata, key.lstrip("/").lower(), None)
    if raw is None:
        return None
    value = str(raw).strip()
    return value or None


def _status_hint(text_char_count: int, min_text_chars: int) -> str:
    if text_char_count >= min_text_chars:
        return "full"
    return "snippet_fallback"


def _download_pdf(spec: dict[str, Any]) -> tuple[io.BytesIO | None, dict[str, Any], str | None, str | None]:
    url = spec.get("url") or ""
    timeout = tuple(spec.get("timeout") or DEFAULT_TIMEOUT)
    max_bytes = int(spec.get("max_bytes") or DEFAULT_MAX_BYTES)
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "application/pdf,application/octet-stream;q=0.8,*/*;q=0.5",
    }
    started = time.monotonic()
    try:
        resp = requests.get(
            url,
            headers=headers,
            timeout=timeout,
            allow_redirects=True,
            stream=True,
        )
    except (requests.ConnectTimeout, requests.ReadTimeout) as exc:
        return None, {}, "timeout", f"timeout: {exc}"
    except requests.RequestException as exc:
        return None, {}, "download_failed", f"download failed: {exc}"

    try:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        metadata = {
            "http_status": resp.status_code,
            "final_url": resp.url,
            "content_type": resp.headers.get("Content-Type"),
            "content_length": resp.headers.get("Content-Length"),
            "elapsed_ms": elapsed_ms,
        }
        if resp.status_code in (401, 402, 403, 451):
            return None, metadata, "blocked_or_paywall", f"HTTP {resp.status_code}"
        if resp.status_code == 429:
            return None, metadata, "rate_limited", "HTTP 429"
        if resp.status_code >= 400:
            return None, metadata, "download_failed", f"HTTP {resp.status_code}"

        content_length = resp.headers.get("Content-Length")
        if content_length:
            try:
                declared_size = int(content_length)
            except ValueError:
                declared_size = None
            if declared_size is not None and declared_size > max_bytes:
                return (
                    None,
                    metadata,
                    "download_failed",
                    f"download exceeds max_bytes: Content-Length {declared_size} > {max_bytes}",
                )

        iter_content = getattr(resp, "iter_content", None)
        if not callable(iter_content):
            return None, metadata, "download_failed", "response missing iter_content"

        chunks = []
        total = 0
        for chunk in iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
            if not chunk:
                continue
            if total + len(chunk) > max_bytes:
                return (
                    None,
                    metadata,
                    "download_failed",
                    f"download exceeds max_bytes during read: > {max_bytes}",
                )
            chunks.append(chunk)
            total += len(chunk)
        content = b"".join(chunks)
        if not content:
            return None, metadata, "download_failed", "empty PDF response"
        return io.BytesIO(content), metadata, None, None
    finally:
        close = getattr(resp, "close", None)
        if callable(close):
            close()


def _open_pdf_stream(spec: dict[str, Any]) -> tuple[io.BufferedIOBase | io.BytesIO | None, dict[str, Any], str | None, str | None]:
    path = spec.get("path")
    url = spec.get("url")
    if path and url:
        return None, {}, None, "provide only one of path or url"
    if path:
        pdf_path = Path(path)
        if not pdf_path.exists():
            return None, {}, None, f"missing PDF path: {path}"
        if not pdf_path.is_file():
            return None, {}, None, f"PDF path is not a file: {path}"
        return pdf_path.open("rb"), {}, None, None
    if url:
        return _download_pdf(spec)
    return None, {}, None, "missing path or url"


def extract_source(spec: dict[str, Any]) -> dict[str, Any]:
    """Extract one PDF source spec. Returns a JSON-ready result dict."""
    result = _empty_result(spec)
    max_chars = int(spec.get("max_chars") or DEFAULT_MAX_CHARS)
    min_text_chars = int(spec.get("min_text_chars") or DEFAULT_MIN_TEXT_CHARS)
    max_pages = int(spec.get("max_pages") or DEFAULT_MAX_PAGES)

    if PdfReader is None:
        result["error"] = "missing dependency: pypdf"
        return result

    stream, download_metadata, soft_fail, error = _open_pdf_stream(spec)
    result["metadata"].update(download_metadata)
    if error:
        result["error"] = error
        result["soft_fail"] = soft_fail
        if soft_fail in ("blocked_or_paywall", "rate_limited", "download_failed", "timeout"):
            result["body_status_hint"] = "paywall_stub"
        return result

    try:
        assert stream is not None
        try:
            reader = PdfReader(stream)
            page_texts = []
            stored_chars = 0
            observed_text_char_count = 0
            page_count = len(getattr(reader, "pages", []))
            metadata = getattr(reader, "metadata", None)
            for index, page in enumerate(reader.pages):
                if index >= max_pages:
                    break
                try:
                    raw_page_text = page.extract_text() or ""
                except Exception:  # noqa: BLE001 - keep extracting later pages
                    raw_page_text = ""
                if raw_page_text:
                    separator_budget = 1 if page_texts else 0
                    remaining = max_chars - stored_chars - separator_budget
                    page_text, observed_chars = _normalize_text_limited(raw_page_text, remaining)
                    observed_text_char_count += observed_chars
                    if page_text:
                        page_texts.append(page_text)
                        stored_chars += separator_budget + len(page_text)
                if stored_chars >= max_chars:
                    break
        finally:
            close = getattr(stream, "close", None)
            if callable(close):
                close()
    except Exception as exc:  # noqa: BLE001 - surface parser failure as JSON
        result["error"] = f"PDF parse failed: {exc}"
        return result

    text = "\n".join(page_texts)
    text_char_count = observed_text_char_count
    result["metadata"].update(
        {
            "page_count": page_count,
            "title": _metadata_value(metadata, "/Title"),
            "author": _metadata_value(metadata, "/Author"),
        }
    )
    result["text"] = text[:max_chars]
    result["text_char_count"] = text_char_count
    result["body_status_hint"] = _status_hint(text_char_count, min_text_chars)
    return result


def _load_specs_from_stdin() -> list[dict[str, Any]]:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid stdin JSON: {exc}") from exc
    if isinstance(payload, dict) and isinstance(payload.get("sources"), list):
        return payload["sources"]
    if isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list):
        return payload
    raise ValueError("stdin JSON must be an object, list, or object with sources[]")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract compact text from public PDFs.")
    parser.add_argument("--stdin", action="store_true", help="read JSON spec or {sources: []} from stdin")
    parser.add_argument("--source-id", help="source identifier for a single PDF")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--path", help="local PDF path")
    group.add_argument("--url", help="public PDF URL")
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    parser.add_argument("--min-text-chars", type=int, default=DEFAULT_MIN_TEXT_CHARS)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    try:
        if args.stdin:
            specs = _load_specs_from_stdin()
        else:
            if not (args.path or args.url):
                parser.error("one of --path or --url is required unless --stdin is used")
            specs = [
                {
                    "source_id": args.source_id or "",
                    "path": args.path,
                    "url": args.url,
                    "max_chars": args.max_chars,
                    "min_text_chars": args.min_text_chars,
                    "max_bytes": args.max_bytes,
                    "max_pages": args.max_pages,
                }
            ]
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    results = [extract_source(spec) for spec in specs]
    output = {"extracted_at": _now_iso(), "results": results}
    print(json.dumps(output, ensure_ascii=False, separators=(",", ":")))
    if results and all(result.get("soft_fail") for result in results):
        return 10
    if any(result.get("error") and not result.get("soft_fail") for result in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
