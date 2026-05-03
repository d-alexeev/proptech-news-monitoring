<!-- Archived from PLANS.md by RT-M8 Plan Context Hygiene. Human review history only; not runtime context. -->

## CR Fix: cr_telegram_formatting__20260422

**Source:** `.state/change-requests/2026-04-22/cr_telegram_formatting__20260422.json`
**Severity:** medium | **Scope:** adapter + mode prompt + delivery contract + tests

### Root cause

The digest template is written in GFM, but Telegram MarkdownV2 does not support
`#`-headings, `---` dividers, or `**double-star**` bold. The existing
`auto_escape=True` in `telegram_send.py` conflicts with intentional markdown syntax.
Operator-only content (`.state/` path refs, full `run_id`) leaks into Telegram messages.
The digest file was written via `Edit` instead of `Write`, leaving stale content in the tail.

**Decision:** switch `telegram_digest` and `telegram_weekly_digest` to HTML parse_mode.
`telegram_alert` stays on MarkdownV2.

### CR-M1 — tools/telegram_send.py

- Switch `telegram_digest` / `telegram_weekly_digest` profiles to `parse_mode: HTML`
- Add `convert_md_to_html(body)`: `## H` → `<b>H</b>`, `**t**`/`*t*` → `<b>t</b>`,
  `[t](u)` → `<a href="u">t</a>`, `` `c` `` → `<code>c</code>`, `---` → blank line,
  plain-text HTML escaping (`&`, `<`, `>`)
- Add `strip_operator_content(body)`: remove blockquote lines containing `.state/` paths
- Add `strip_run_id_from_footer(body)`: replace full run_id in footer with date + mode only
- Keep `escape_body_for_markdown_v2` for `telegram_alert`

### CR-M4 — tools/test_telegram_send.py (3 fixtures from CR)

1. `test_telegram_format_html` — `convert_md_to_html` unit test
2. `test_telegram_no_internal_notes` — `strip_operator_content` unit test
3. `test_digest_file_full_overwrite` — Write-not-Edit regression

### CR-M2 — cowork/modes/build_daily_digest.md

Add **"Delivery constraints"** section:
- Operator metadata (`.state/` paths, full `run_id`) → only in `run_manifest`, not in body
- Digest file → always `Write` (full overwrite), never `Edit`
- Body formatting: adapter normalises GFM to HTML; standard GFM is acceptable in .md

### CR-M3 — cowork/adapters/telegram_format.md (new) + contracts.md

- Document parse_mode = HTML rationale and GFM-to-HTML mapping
- Define "operator content" and strip rule
- Note `telegram_alert` stays on MarkdownV2
- Add reference in `contracts.md`

### CR Acceptance criteria

- [ ] Dry-run on `digests/2026-04-22-daily-digest.md` produces HTML with no `#`-headings,
      no `---`, no `.state/` paths, no full run_id
- [ ] All three fixture tests pass (`python3 -m pytest tools/test_telegram_send.py -v`)
- [ ] `telegram_alert` profile behaviour unchanged
- [ ] `contracts.md` references the new adapter doc
- [ ] CR status updated to `resolved`
