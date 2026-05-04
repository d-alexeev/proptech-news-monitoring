# Weekday Digest Run Review: YYYY-MM-DD

## Review Metadata

| Field | Value |
| --- | --- |
| Schedule | `weekday_digest` |
| Run date | `YYYY-MM-DD` |
| Reviewer | `name-or-role` |
| Review status | `production_ready`, `partial`, `externally_blocked`, or `failed` |
| Local evidence window | `.state/` local-only, retained until `YYYY-MM-DD` |
| Tracked summary prepared from | sanitized operator review, not raw JSONL |

## Outcome Summary

| Area | Outcome | Evidence |
| --- | --- | --- |
| Source discovery | `completed`, `partial`, or `failed` | source count, failed source IDs, sanitized class |
| Enrichment | `completed`, `partial`, `snippet_fallback_only`, or `failed` | enriched count and evidence status counts |
| Digest generation | `completed`, `partial`, `non_canonical`, or `failed` | digest path and item count |
| QA/review | `passed`, `warnings`, or `failed` | compact reviewer finding summary |
| Telegram delivery | `sent`, `dry_run_only`, `delivery_failed_dns`, `delivery_failed_http`, `delivery_failed_api`, or `not_attempted` | sanitized status only |

## Source Outcomes

| Source or group | Status | Evidence reference | Notes |
| --- | --- | --- | --- |
| `daily_core` | `completed` | `N items discovered` | no raw HTML copied |
| `example_source_id` | `timeout` | `source-level soft fail` | sanitized error class only |

## Delivery Outcome

| Field | Value |
| --- | --- |
| Delivery profile | `telegram_digest` |
| Delivery mode | `dry_run` or `live` |
| Delivery status | `sent`, `delivery_failed_dns`, `delivery_failed_http`, `delivery_failed_api`, `delivery_failed_unknown`, or `not_attempted` |
| Sanitized endpoint | `https://api.telegram.org/<bot-token-redacted>/sendMessage` |
| Message parts | `N` |
| Error summary | `<redacted or none>` |

Do not paste full Bot API URLs, bot tokens, chat IDs, request bodies, or raw
exception payloads.

## Review Notes

- `Status note`: concise operator-readable conclusion.
- `Evidence note`: compact source/digest/delivery facts needed for launch
  review.
- `Follow-up`: change request ID or `none`.

## Safety Checklist

- [ ] No `.state/` artifact contents are pasted into this file.
- [ ] No full Telegram Bot API URL containing `/bot...` appears in this file.
- [ ] No bot token, chat ID, proxy credential, cookie, or `.env` value appears in
      this file.
- [ ] No bulky HTML body, scraped page body, or full article text appears in this
      file.
- [ ] Secret scan command from `docs/run-reviews/README.md` returned no matches.
