# Telegram Delivery Format Contract

**Applies to:** `tools/telegram_send.py`, `cowork/modes/build_daily_digest.md`,
`cowork/modes/build_weekly_digest.md`

**Status:** active — supersedes the previous MarkdownV2-for-digest approach.
**Introduced:** 2026-04-22 (cr_telegram_formatting__20260422)

---

## Parse mode by profile

| Profile                | parse_mode | Rationale                                                     |
|------------------------|------------|---------------------------------------------------------------|
| `telegram_digest`      | HTML       | Digest bodies use GFM headings/dividers that MarkdownV2 cannot render |
| `telegram_weekly_digest` | HTML     | Same as above                                                 |
| `telegram_alert`       | MarkdownV2 | Short messages; no headings or dividers; existing escaping is correct |

**Why HTML and not MarkdownV2 for digests:**
Telegram MarkdownV2 does not support `#`-headings or `---` dividers.
The `auto_escape` mechanism in the adapter escapes all special characters, which
conflicts with intentional bold/link formatting. HTML mode has unambiguous tags
(`<b>`, `<a href>`, `<code>`) and does not require backslash escaping of punctuation.

---

## GFM-to-HTML mapping (applied by `convert_md_to_html`)

| GFM construct            | Telegram HTML output               | Notes                              |
|--------------------------|------------------------------------|------------------------------------|
| `# Heading`              | `<b>Heading</b>`                   | All heading levels 1–6             |
| `## Heading`             | `<b>Heading</b>`                   |                                    |
| `**bold**`               | `<b>bold</b>`                      |                                    |
| `*bold*`                 | `<b>bold</b>`                      | Single-star also maps to bold      |
| `[text](url)`            | `<a href="url">text</a>`           |                                    |
| `` `code` ``             | `<code>code</code>`                |                                    |
| `---` (horizontal rule)  | *(removed)*                        | Use blank lines for visual breaks  |
| `&`, `<`, `>` in prose   | `&amp;`, `&lt;`, `&gt;`            | HTML-escaped in plain-text segments |

Telegram HTML does **not** support: tables, strikethrough (in older clients),
nested formatting, raw HTML beyond the allowed tag set.

---

## Operator content — strip rules

The following content must be stripped before sending (`strip_operator_content`,
`strip_run_id_from_footer` in `telegram_send.py`):

1. **Blockquote lines containing `.state/` paths** — operator context notes that
   reference internal run artifacts must not appear in subscriber-facing messages.
   Pattern: lines beginning with `>` that contain `.state/`.

2. **Full run_id in the footer** — the timestamped run_id
   (e.g. `build_daily_digest__20260422T230500Z__daily_core`) is excessive for
   readers. The footer may retain the mode name and date only.

These strips are applied automatically by the adapter for HTML-mode profiles.
Digest authors should not rely on the adapter to fix structural operator leaks;
the mode prompt (`build_daily_digest.md`) forbids operator content in the body.

---

## Delivery failure reporting

`tools/telegram_send.py` must sanitize Telegram request exceptions before they
reach stdout/stderr JSON or delivery metadata. Token-bearing Bot API URLs such as
`https://api.telegram.org/bot.../sendMessage` are rewritten to preserve only the
endpoint path, for example `https://api.telegram.org/<bot-token-redacted>/sendMessage`.

Failed sends keep the `errors` array, but each entry is a structured record:

- `part` — zero-based message part index
- `classification` — one of `delivery_failed_dns`, `delivery_failed_http`,
  `delivery_failed_api`, or `delivery_failed_unknown`
- `message` — sanitized operator-facing detail

The top-level `delivery_status` mirrors the first error classification when
delivery fails, or `delivered` after successful live delivery.

`TELEGRAM_MESSAGE_THREAD_ID=` with an empty value is normalized as unset. The
JSON report emits `message_thread_id: null` and the Telegram payload omits
`message_thread_id`.

---

## What digest authors must ensure

See `cowork/modes/build_daily_digest.md` → "Delivery constraints" for the full rules.
In summary:

- Do not embed `.state/` paths or full run_ids in the digest body.
- Do not use blockquote lines for operator notes in the digest body.
- Write the digest file with `Write` (full overwrite), never `Edit`.
- Standard GFM formatting is acceptable; the adapter converts it.

---

## Testing

Fixtures: `tools/test_telegram_send.py`

- `test_telegram_format_html` — verifies `convert_md_to_html`
- `test_telegram_no_internal_notes` — verifies `strip_operator_content`
- `test_digest_file_full_overwrite` — documents the Write-not-Edit contract
- `test_strip_run_id_from_footer` — verifies `strip_run_id_from_footer`
- `test_telegram_delivery_error_redaction` — verifies Bot API URL redaction and classification
- `test_telegram_main_redacts_send_exception` — verifies JSON output does not leak token URLs

Run: `python3 -m pytest tools/test_telegram_send.py -v`
