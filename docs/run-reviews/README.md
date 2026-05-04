# Run Reviews

Tracked run reviews preserve launch evidence without committing `.state/`
runtime artifacts. Use this directory for short, human-written summaries after
manual launch checks, scheduled dry runs, or production-readiness reviews.

## What To Track

Create one Markdown summary per reviewed run using
`YYYY-MM-DD-weekday-digest-template.md` as the starting point. The summary should
record:

- schedule, run date, reviewer, and review status;
- source discovery outcomes by source or source group;
- enrichment and digest status outcomes;
- review/QA outcome;
- Telegram delivery outcome and sanitized error classification, if any;
- compact evidence references such as digest paths, source IDs, status labels,
  counts, and redacted error classes.

Use redacted placeholders only for sensitive values, for example
`<telegram-bot-token-redacted>`, `<telegram-chat-id-redacted>`, and
`https://api.telegram.org/<bot-token-redacted>/sendMessage`.

## What Not To Track

Do not commit:

- `.state/` files, including `.state/codex-runs/*-events.jsonl`;
- raw Telegram bot tokens, chat IDs, or full Bot API URLs containing `/bot...`;
- full JSONL event logs or long copied agent transcripts;
- bulky HTML bodies, scraped page bodies, or full article text;
- local `.env` values, proxy URLs with credentials, cookies, or session headers.

If a field is needed for review but unsafe to publish, replace the value with a
redacted placeholder and keep the original only in local `.state/` evidence.

## Local Retention And Quarantine

`.state/` remains git-ignored and is the local evidence store. During launch
hardening, keep relevant local run evidence long enough to support review, then
delete or archive it according to the operator's retention policy. A practical
default is to retain launch-review evidence for 30 days.

Treat unsafe JSONL event logs as local-only. If a log may contain a secret,
full Bot API URL, cookie, proxy credential, or bulky scraped body:

1. leave it out of tracked docs;
2. move or copy it under a local quarantine path such as
   `.state/quarantine/YYYY-MM-DD/`;
3. restrict access to the local `.state/` tree before sharing the machine or
   copying artifacts;
4. summarize only sanitized outcomes in `docs/run-reviews/`.

Do not redact or rewrite historical `.state/` logs unless the operator
explicitly approves that cleanup.

## Secret Scan

Before committing a run review, scan tracked review docs and the operator README
for Telegram Bot API token URLs:

```bash
git ls-files docs/run-reviews ops/codex-cli/README.md \
  | xargs rg -n -P 'https://api\.telegram\.org/bot[0-9]+:[A-Za-z0-9_-]+|/bot[0-9]+:[A-Za-z0-9_-]+'
```

The command should return no matches. It is intentionally narrow and no-network:
it looks for concrete Telegram bot token URL shapes in tracked review material.
