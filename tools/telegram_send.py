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
  TELEGRAM_MESSAGE_THREAD_ID   (optional — forum topic id; empty is unset)

Usage:
  cat digests/2026-04-21-daily-digest.md | \
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
    "delivery_status": "delivered",
    "errors": []
  }

Failed delivery reports keep `errors` but use structured, sanitized records
with classification values such as `delivery_failed_dns`, `delivery_failed_http`,
`delivery_failed_api`, or `delivery_failed_unknown`.

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

import russian_text_gate


TELEGRAM_API_BASE = "https://api.telegram.org"
RUSSIAN_DELIVERY_PROFILES = {"telegram_digest", "telegram_weekly_digest"}

BUILT_IN_PROFILES: dict[str, dict] = {
    "telegram_digest": {
        "enabled": True,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "split_long_messages": True,
        "max_message_length": 3800,
        "title_template": "PropTech Monitor | {date}",
    },
    "telegram_weekly_digest": {
        "enabled": True,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "split_long_messages": True,
        "max_message_length": 3800,
        "title_template": "PropTech Weekly | {date}",
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
_TELEGRAM_BOT_URL_RE = re.compile(
    r"(?P<base>https://api\.telegram\.org)?/bot[^\s\"'<>/]+(?P<path>/[^\s\"'<>]*)?"
)
_DNS_ERROR_RE = re.compile(
    r"NameResolutionError|Temporary failure in name resolution|"
    r"Failed to resolve|nodename nor servname|Name or service not known|getaddrinfo|DNS",
    re.IGNORECASE,
)


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


def sanitize_delivery_error(exc: BaseException | str) -> str:
    """Return a delivery error string with Telegram bot-token URLs redacted."""
    message = str(exc)

    def _replace(match: re.Match[str]) -> str:
        base = match.group("base") or ""
        path = match.group("path") or ""
        endpoint = path.split("?", 1)[0]
        return f"{base}/<bot-token-redacted>{endpoint}"

    return _TELEGRAM_BOT_URL_RE.sub(_replace, message)


def classify_delivery_error(exc: BaseException | str) -> str:
    """Classify Telegram delivery failures for operator-facing reports."""
    message = str(exc)
    if _DNS_ERROR_RE.search(message):
        return "delivery_failed_dns"
    if isinstance(exc, requests.HTTPError):
        return "delivery_failed_http"
    if "telegram api error" in message.lower():
        return "delivery_failed_api"
    if "status=" in message.lower() or "http" in message.lower():
        return "delivery_failed_http"
    return "delivery_failed_unknown"


def delivery_error_record(part_index: int, exc: BaseException) -> dict[str, object]:
    """Build a sanitized, classified delivery error record."""
    classification = classify_delivery_error(exc)
    return {
        "part": part_index,
        "classification": classification,
        "message": f"part {part_index}: {sanitize_delivery_error(exc)}",
    }


def validate_delivery_language(body: str, *, profile_name: str, allow_non_russian: bool) -> None:
    if allow_non_russian or profile_name not in RUSSIAN_DELIVERY_PROFILES:
        return
    russian_text_gate.require_russian_text(body, field_path=f"{profile_name}.body")

# ---------------------------------------------------------------------------
# HTML conversion helpers (for parse_mode=HTML profiles)
# ---------------------------------------------------------------------------

# Telegram HTML supports: <b>, <i>, <u>, <s>, <a href>, <code>, <pre>.
# We map the GFM subset used in digests to this set.

_HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)
_BOLD_DOUBLE_RE = re.compile(r"\*\*(.+?)\*\*")
_BOLD_SINGLE_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
_LINK_RE = re.compile(r"\[([^\[\]]+)\]\(([^()\s]+)\)")
_CODE_RE = re.compile(r"`([^`\n]+)`")
_HR_RE = re.compile(r"^---+\s*$", re.MULTILINE)

# Characters that must be escaped in HTML plain-text segments.
_HTML_ESCAPE = str.maketrans({"&": "&amp;", "<": "&lt;", ">": "&gt;"})

# Pipe-table detection.
_PIPE_ROW_RE = re.compile(r"^\|.+\|[ \t]*$")
_PIPE_SEP_RE = re.compile(r"^\|[-:| \t]+\|[ \t]*$")


def _escape_html(text: str) -> str:
    return text.translate(_HTML_ESCAPE)


def _convert_pipe_tables(body: str) -> str:
    """Convert GFM pipe tables to Telegram-friendly bullet lists.

    Detects blocks of consecutive | rows, identifies the optional header row
    and separator, and emits data rows as `• cell1 | cell2 | …`.  Inline
    formatting within cells is left intact for later processing by
    _convert_inline().
    """
    lines = body.split("\n")
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not _PIPE_ROW_RE.match(line):
            result.append(line)
            i += 1
            continue
        # Collect consecutive pipe rows into a table block
        block: list[str] = []
        while i < len(lines) and _PIPE_ROW_RE.match(lines[i]):
            block.append(lines[i])
            i += 1
        # Classify rows: separator rows are structural, rest are data/header
        sep_indices = {j for j, r in enumerate(block) if _PIPE_SEP_RE.match(r.strip())}
        parsed: list[list[str]] = []
        for j, row in enumerate(block):
            if j in sep_indices:
                continue
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            parsed.append(cells)
        # rows[0] = header when there was a separator at index 1; skip it in output
        # (Telegram can't render table headers distinctly, just treat all as data)
        has_header = bool(sep_indices) and min(sep_indices, default=99) == 1
        data_rows = parsed[1:] if (has_header and len(parsed) > 1) else parsed
        for row in data_rows:
            content = " | ".join(c for c in row if c)
            if content:
                result.append(f"• {content}")
    return "\n".join(result)


def convert_md_to_html(body: str) -> str:
    """Convert a GFM-subset digest body to Telegram HTML.

    Handles (in order):
    - `---` horizontal rules → removed
    - GFM pipe tables → bullet list (`• cell1 | cell2 | …`)
    - `# / ## / ###` headings → <b>TEXT</b>
    - `[text](url)` links → <a href="url">text</a>
    - `**bold**` and `*bold*` → <b>bold</b>
    - `code` → <code>code</code>
    - Plain-text segments → HTML-escaped (&, <, >)

    The conversion is line-aware for headings/HRs/tables and span-aware for
    inline formatting so that plain-text characters are escaped without
    double-processing already-converted spans.
    """
    # Step 1: horizontal rules → removed (before any inline processing)
    body = _HR_RE.sub("", body)

    # Step 1.5: pipe tables → bullet list (before heading/inline steps)
    body = _convert_pipe_tables(body)

    # Step 2: headings → <b>…</b>
    body = _HEADING_RE.sub(lambda m: f"<b>{_escape_html(m.group(1))}</b>", body)

    # Step 3: process inline spans per line to escape plain text correctly.
    # We tokenise each "segment" between recognised spans so that punctuation
    # in prose is HTML-escaped while span content is handled separately.
    def _convert_inline(text: str) -> str:
        # Order matters: links first (contain parens that would confuse bold),
        # then double-star bold, then single-star bold, then code.
        combined = re.compile(
            r"(?P<link>\[(?P<ltext>[^\[\]]+)\]\((?P<lurl>[^()\s]+)\))"
            r"|(?P<bold2>\*\*(?P<b2text>.+?)\*\*)"
            r"|(?P<bold1>(?<!\*)\*(?!\*)(?P<b1text>.+?)(?<!\*)\*(?!\*))"
            r"|(?P<code>`(?P<ctext>[^`\n]+)`)"
        )
        out: list[str] = []
        cursor = 0
        for m in combined.finditer(text):
            # Escape plain text before this span
            out.append(_escape_html(text[cursor:m.start()]))
            if m.group("link"):
                out.append(
                    f'<a href="{_escape_html(m.group("lurl"))}">'
                    f"{_escape_html(m.group('ltext'))}</a>"
                )
            elif m.group("bold2"):
                out.append(f"<b>{_escape_html(m.group('b2text'))}</b>")
            elif m.group("bold1"):
                out.append(f"<b>{_escape_html(m.group('b1text'))}</b>")
            elif m.group("code"):
                out.append(f"<code>{_escape_html(m.group('ctext'))}</code>")
            cursor = m.end()
        out.append(_escape_html(text[cursor:]))
        return "".join(out)

    # Apply inline conversion to lines that were NOT already converted to tags
    # by the heading step (those start with "<b>" and end with "</b>").
    lines = body.split("\n")
    result: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("<b>") and stripped.endswith("</b>"):
            result.append(line)  # heading already converted, leave as-is
        else:
            result.append(_convert_inline(line))
    return "\n".join(result)


# Pattern for blockquote lines that contain .state/ path references.
# These are operator notes that must not appear in subscriber-facing messages.
_OPERATOR_NOTE_RE = re.compile(
    r"^>[ \t].*\.state/.*$", re.MULTILINE
)

# Pattern for a full run_id in the digest footer line.
# Captures the mode name and replaces the full timestamped id with just the mode.
_RUN_ID_RE = re.compile(
    r"\brun:\s*(build_\w+?)__\d{8}T\d{6}Z__\w+"
)


def strip_operator_content(body: str) -> str:
    """Remove blockquote lines that contain .state/ path references.

    These lines are operator context notes (e.g. references to previous runs)
    that should appear in run_manifest but not in subscriber-facing messages.
    A blank line is left in place to preserve paragraph spacing.
    """
    return _OPERATOR_NOTE_RE.sub("", body)


def strip_run_id_from_footer(body: str) -> str:
    """Replace the full run_id in the footer with just the mode name.

    Converts:
      run: build_daily_digest__20260422T230500Z__daily_core
    to:
      run: build_daily_digest
    """
    return _RUN_ID_RE.sub(r"run: \1", body)


# ---------------------------------------------------------------------------
# Pre-send validation
# ---------------------------------------------------------------------------

_VALIDATE_RULES: list[dict] = [
    {
        "check_id": "raw_md_heading",
        "pattern": re.compile(r"^#{1,6}\s+.+$", re.MULTILINE),
        "symptom": "Raw markdown heading(s) not converted to <b> — will display as literal # text",
        "severity": "error",
    },
    {
        "check_id": "raw_hr",
        "pattern": re.compile(r"^-{3,}\s*$", re.MULTILINE),
        "symptom": "Horizontal rule(s) not removed — will display as literal ---",
        "severity": "error",
    },
    {
        "check_id": "raw_double_star",
        "pattern": re.compile(r"\*\*[^*\n]+\*\*"),
        "symptom": "Double-star bold (**text**) not converted to <b> — will display as literal **",
        "severity": "error",
    },
    {
        "check_id": "pipe_table",
        "pattern": re.compile(r"^\|.+\|[ \t]*$", re.MULTILINE),
        "symptom": "Pipe table row(s) not converted — renders as raw | col | text in Telegram",
        "severity": "warning",
    },
    {
        "check_id": "state_path_leak",
        "pattern": re.compile(r"\.state/"),
        "symptom": "Operator .state/ path leaked into subscriber-facing content",
        "severity": "error",
    },
    {
        "check_id": "full_run_id",
        "pattern": re.compile(r"\bbuild_\w+?__\d{8}T\d{6}Z__\w+"),
        "symptom": "Full timestamped run_id not stripped — exposes internal run metadata",
        "severity": "warning",
    },
]


def validate_html_output(html: str) -> list[dict]:
    """Check converted HTML for formatting issues before Telegram delivery.

    Runs each rule in _VALIDATE_RULES against the final output.  Returns a
    list of issue dicts (empty list = clean).  Each dict has keys:
      check_id, severity ('error' | 'warning'), symptom, match_count, examples.

    Errors indicate content that will definitely look broken in Telegram.
    Warnings indicate content that is suboptimal but may still be readable.
    """
    issues: list[dict] = []
    for rule in _VALIDATE_RULES:
        matches = rule["pattern"].findall(html)
        if matches:
            issues.append({
                "check_id": rule["check_id"],
                "severity": rule["severity"],
                "symptom": rule["symptom"],
                "match_count": len(matches),
                "examples": [str(m)[:120] for m in matches[:3]],
            })
    return issues


def write_presend_cr(
    issues: list[dict],
    *,
    profile: str,
    date: str,
    repo_root: Path | None = None,
) -> Path:
    """Write an auto-generated pre-send validation CR.

    The CR is written to .state/change-requests/{date}/cr_presend_validation__{ts}.json.
    Returns the path of the written file.
    """
    root = repo_root or REPO_ROOT
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    cr_dir = root / ".state" / "change-requests" / date
    cr_dir.mkdir(parents=True, exist_ok=True)
    cr_path = cr_dir / f"cr_presend_validation__{ts}.json"

    worst = "error" if any(i["severity"] == "error" for i in issues) else "warning"
    cr = {
        "request_id": f"cr_presend_validation__{ts}",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "profile": profile,
        "stage": "pre_send_validation",
        "failure_type": "validation_error",
        "severity": worst,
        "symptoms": [i["symptom"] for i in issues],
        "issues": issues,
        "status": "new",
        "owner": "telegram_send",
        "notes": (
            "Auto-generated by validate_html_output() in tools/telegram_send.py. "
            "Fix the root cause in convert_md_to_html() or the digest template, "
            "then re-run. Use --force to bypass validation and send anyway."
        ),
    }
    cr_path.write_text(json.dumps(cr, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return cr_path


# ---------------------------------------------------------------------------

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
            last_exc = RuntimeError(
                f"telegram retryable http status={resp.status_code} retry_after={retry_after}"
            )
            time.sleep(max(1, retry_after))
            continue

        if resp.status_code >= 500:
            last_exc = RuntimeError(f"telegram retryable http status={resp.status_code}")
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
    p.add_argument(
        "--force",
        action="store_true",
        help="send even if pre-send validation finds issues (CR is still written)",
    )
    p.add_argument(
        "--allow-non-russian",
        action="store_true",
        help="operator override for non-Russian digest bodies",
    )
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
    validate_delivery_language(body, profile_name=args.profile, allow_non_russian=args.allow_non_russian)

    date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    use_mdv2 = (profile.get("parse_mode") or "").lower() == "markdownv2"
    use_html = (profile.get("parse_mode") or "").upper() == "HTML"
    auto_escape = bool(profile.get("auto_escape", use_mdv2))

    if use_html:
        # Strip operator-only content before HTML conversion
        body = strip_operator_content(body)
        body = strip_run_id_from_footer(body)
        body = convert_md_to_html(body)

        # Pre-send validation: check the converted HTML for formatting issues.
        issues = validate_html_output(body)
        if issues:
            cr_path = write_presend_cr(issues, profile=args.profile, date=date_str)
            error_count = sum(1 for i in issues if i["severity"] == "error")
            warn_count = sum(1 for i in issues if i["severity"] == "warning")
            summary = f"{error_count} error(s), {warn_count} warning(s)"
            print(
                f"pre-send validation: {summary} — CR written to {cr_path}",
                file=sys.stderr,
            )
            for issue in issues:
                print(
                    f"  [{issue['severity']}] {issue['check_id']}: {issue['symptom']} "
                    f"(×{issue['match_count']})",
                    file=sys.stderr,
                )
            if error_count > 0 and not args.force and not args.dry_run:
                print(
                    "Blocked: fix validation errors or re-run with --force to send anyway.",
                    file=sys.stderr,
                )
                sys.exit(3)
    elif auto_escape and use_mdv2:
        body = escape_body_for_markdown_v2(body)

    if not args.no_title:
        title_tpl = profile.get("title_template") or ""
        if title_tpl:
            title_line = title_tpl.format(date=date_str)
            if use_html:
                title_line = _escape_html(title_line)
                body = f"<b>{title_line}</b>\n\n{body.lstrip()}"
            else:
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
    errors: list[dict[str, object]] = []

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
            errors.append(delivery_error_record(idx, exc))
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
        "delivery_status": errors[0]["classification"] if errors else "delivered",
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
        print(
            f"unhandled_error: {exc.__class__.__name__}: {sanitize_delivery_error(exc)}",
            file=sys.stderr,
        )
        sys.exit(1)
