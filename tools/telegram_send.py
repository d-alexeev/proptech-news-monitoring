#!/usr/bin/env python3
"""
telegram_send.py — Telegram delivery for PropTech News Monitoring.

Reads a markdown body from stdin and sends it to Telegram according to a
delivery profile defined in config/runtime/schedule_bindings.yaml.

Profiles are resolved by name (--profile) with the following defaults,
mirroring schedule_bindings.yaml#delivery_profiles:

  telegram_digest         parse_mode=MarkdownV2, split, max=3800, title="PropTech Monitor | {date}"
  telegram_weekly_digest  parse_mode=MarkdownV2, split, max=3800, title="PropTech Weekly | {date}"
  telegram_alert          parse_mode=MarkdownV2, no split, max=2500, title="PropTech Alert | {date}"

MarkdownV2 profiles with auto_escape=True (the default) run the body through
`escape_body_for_markdown_v2`, which preserves the safe subset *bold*, `code`,
and [text](url) and backslash-escapes everything else. This lets digest authors
freely use punctuation, dates, and source_ids like `costar_homes` without
hitting Telegram's "can't find end of the entity" parse errors.

If config/runtime/schedule_bindings.yaml is present and PyYAML is available,
values from the file override the defaults. Missing PyYAML is fine — built-in
defaults kick in.

Required env:
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID
  TELEGRAM_MESSAGE_THREAD_ID   (optional — forum topic id)

Usage:
  cat digests/2026-04-21-daily.md | \
    python3 tools/telegram_send.py \
      --profile telegram_digest \
      --date 2026-04-21 \
      [--dry-run]

Output (stdout, one JSON doc):

  {
    "delivered_at": "2026-04-21T09:01:12Z",
    "profile": "telegram_digest",
    "chat_id": "-100...",
    "message_thread_id": "...",
    "parts_sent": 2,
    "message_ids": [12345, 12346],
    "errors": []
  }

Exit codes:
  0  delivered (or dry-run ok)
  1  send failed (network / Telegram API error)
  2  invalid arguments or missing env
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


TELEGRAM_API_BASE = "https://api.telegram.org"

BUILT_IN_PROFILES: dict[str, dict] = {
    "telegram_digest": {
        "enabled": True,
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": True,
        "split_long_messages": True,
        "max_message_length": 3800,
        "title_template": "PropTech Monitor | {date}",
        "auto_escape": True,
    },
    "telegram_weekly_digest": {
        "enabled": True,
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": True,
        "split_long_messages": True,
        "max_message_length": 3800,
        "title_template": "PropTech Weekly | {date}",
        "auto_escape": True,
    },
    "telegram_alert": {
        "enabled": True,
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": True,
        "split_long_messages": False,
        "max_message_length": 2500,
        "title_template": "PropTech Alert | {date}",
        "auto_escape": True,
    },
}

# Characters that Telegram MarkdownV2 requires to be escaped with a backslash.
# Ref: https://core.telegram.org/bots/api#markdownv2-style
_MDV2_PLAIN_SPECIALS = set("_*[]()~`>#+-=|{}.!\\")
_MDV2_URL_SPECIALS = set(")\\")
_MDV2_CODE_SPECIALS = set("`\\")


def _escape_mdv2(text: str, specials: set[str] = _MDV2_PLAIN_SPECIALS) -> str:
    out: list[str] = []
    for ch in text:
        if ch in specials:
            out.append("\\")
        out.append(ch)
    return "".join(out)


# Tokenizer that understands the "safe" subset digests use:
#   *bold*   [text](url)   `code`   plain text
# Anything else is treated as plain text and escaped per MarkdownV2 rules.
_TOKEN_RE = re.compile(
    r"""
    (?P<link>\[(?P<ltext>[^\[\]]+)\]\((?P<lurl>[^()\s]+)\))
    | (?P<bold>\*(?P<btext>[^*\n]+)\*)
    | (?P<code>`(?P<ctext>[^`\n]+)`)
    """,
    re.VERBOSE,
)


def escape_body_for_markdown_v2(body: str) -> str:
    """Escape a digest body for Telegram MarkdownV2, preserving intended formatting.

    Recognises *bold*, [text](url), `code` spans. Everything else is escaped per
    MarkdownV2 rules so that characters like `_`, `.`, `-`, `!` inside source
    ids, URLs, dates, and pathnames no longer break the parser.
    """
    out: list[str] = []
    cursor = 0
    for m in _TOKEN_RE.finditer(body):
        out.append(_escape_mdv2(body[cursor:m.start()]))
        if m.group("link"):
            text = _escape_mdv2(m.group("ltext"))
            url = _escape_mdv2(m.group("lurl"), _MDV2_URL_SPECIALS)
            out.append(f"[{text}]({url})")
        elif m.group("bold"):
            out.append("*" + _escape_mdv2(m.group("btext")) + "*")
        elif m.group("code"):
            out.append("`" + _escape_mdv2(m.group("ctext"), _MDV2_CODE_SPECIALS) + "`")
        cursor = m.end()
    out.append(_escape_mdv2(body[cursor:]))
    return "".join(out)

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEDULE_PATH = REPO_ROOT / "config" / "runtime" / "schedule_bindings.yaml"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_profile(name: str) -> dict:
    """Return the delivery profile. File overrides built-in defaults when available."""
    profile = dict(BUILT_IN_PROFILES.get(name, {}))
    if not SCHEDULE_PATH.exists():
        return profile
    try:
        import yaml  # type: ignore
    except ImportError:
        return profile
    try:
        data = yaml.safe_load(SCHEDULE_PATH.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001
        print(f"warn: failed to read {SCHEDULE_PATH}: {exc}", file=sys.stderr)
        return profile
    dp = (data.get("delivery_profiles") or {}).get(name) or {}
    merged = {**profile, **dp}
    return merged


def _chunk_markdown(body: str, limit: int) -> list[str]:
    """Split markdown into <= limit chunks, preferring blank-line boundaries."""
    body = body.rstrip() + "\n"
    if len(body) <= limit:
        return [body]
    chunks: list[str] = []
    remaining = body
    while len(remaining) > limit:
        window = remaining[:limit]
        # Prefer last blank line within the window
        split_at = window.rfind("\n\n")
        if split_at < limit // 2:
            split_at = window.rfind("\n")
        if split_at <= 0:
            split_at = limit
        chunks.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()
    if remaining:
        chunks.append(remaining.rstrip())
    return chunks


def _send_chunk(
    bot_token: str,
    chat_id: str,
    text: str,
    *,
    thread_id: str | None,
    parse_mode: str | None,
    disable_preview: bool,
    timeout: int = 30,
) -> dict:
    url = f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage"
    payload: dict[str, object] = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": disable_preview,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if thread_id:
        payload["message_thread_id"] = int(thread_id)

    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            resp = requests.post(url, json=payload, timeout=timeout)
        except requests.RequestException as exc:
            last_exc = exc
            time.sleep(1.5 * (attempt + 1))
            continue

        if resp.status_code == 429:
            retry_after = int(resp.json().get("parameters", {}).get("retry_after", 2))
            time.sleep(max(1, retry_after))
            continue

        if resp.status_code >= 500:
            time.sleep(1.5 * (attempt + 1))
            continue

        try:
            data = resp.json()
        except ValueError:
            raise RuntimeError(f"telegram non-json response status={resp.status_code}")

        if not data.get("ok"):
            raise RuntimeError(
                f"telegram api error status={resp.status_code} "
                f"code={data.get('error_code')} desc={data.get('description')!r}"
            )
        return data["result"]

    raise RuntimeError(f"telegram send failed after retries: {last_exc}")


def _parse_cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PropTech Telegram sender")
    p.add_argument("--profile", required=True, help="delivery profile name")
    p.add_argument("--date", help="substituted into title_template, default=today UTC")
    p.add_argument("--no-title", action="store_true", help="don't prepend title line")
    p.add_argument("--dry-run", action="store_true", help="don't hit Telegram API")
    return p.parse_args()


def main() -> None:
    args = _parse_cli()
    profile = _load_profile(args.profile)
    if not profile:
        print(f"unknown delivery profile: {args.profile}", file=sys.stderr)
        sys.exit(2)

    if profile.get("enabled") is False and not args.dry_run:
        print(f"profile {args.profile} is disabled in config", file=sys.stderr)
        sys.exit(2)

    body = sys.stdin.read()
    if not body.strip():
        print("stdin is empty", file=sys.stderr)
        sys.exit(2)

    date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    use_mdv2 = (profile.get("parse_mode") or "").lower() == "markdownv2"
    auto_escape = bool(profile.get("auto_escape", use_mdv2))

    if auto_escape and use_mdv2:
        body = escape_body_for_markdown_v2(body)

    if not args.no_title:
        title_tpl = profile.get("title_template") or ""
        if title_tpl:
            title_line = title_tpl.format(date=date_str)
            if auto_escape and use_mdv2:
                title_line = _escape_mdv2(title_line)
            body = f"*{title_line}*\n\n{body.lstrip()}"

    limit = int(profile.get("max_message_length", 3800))
    if profile.get("split_long_messages", True):
        parts = _chunk_markdown(body, limit)
    else:
        parts = [body[:limit]]

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    thread_id = os.environ.get("TELEGRAM_MESSAGE_THREAD_ID", "") or None

    if not args.dry_run and (not bot_token or not chat_id):
        print(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required unless --dry-run",
            file=sys.stderr,
        )
        sys.exit(2)

    message_ids: list[int] = []
    errors: list[str] = []

    if args.dry_run:
        report = {
            "delivered_at": _now_iso(),
            "profile": args.profile,
            "dry_run": True,
            "chat_id": chat_id or None,
            "message_thread_id": thread_id,
            "parts_sent": len(parts),
            "part_lengths": [len(p) for p in parts],
            "message_ids": [],
            "errors": [],
        }
        sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        return

    for idx, part in enumerate(parts):
        try:
            result = _send_chunk(
                bot_token,
                chat_id,
                part,
                thread_id=thread_id,
                parse_mode=profile.get("parse_mode"),
                disable_preview=bool(profile.get("disable_web_page_preview", True)),
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"part {idx}: {exc}")
            break
        message_ids.append(int(result.get("message_id")))
        # Telegram rate: <=30 msg/s globally, <=1 msg/s to same chat. Be gentle.
        if idx + 1 < len(parts):
            time.sleep(1.1)

    report = {
        "delivered_at": _now_iso(),
        "profile": args.profile,
        "chat_id": chat_id,
        "message_thread_id": thread_id,
        "parts_sent": len(message_ids),
        "message_ids": message_ids,
        "errors": errors,
    }
    sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"unhandled_error: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
