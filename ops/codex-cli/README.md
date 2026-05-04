# Codex CLI Launch Mode

## Purpose

This directory contains the isolated MVP launch pack for running the PropTech
monitor from a remote server with `codex exec`.

It is an orchestration wrapper, not a new canonical `Claude Cowork` runtime
mode. The canonical source of truth remains:

- `config/runtime/runtime_manifest.yaml`
- `config/runtime/schedule_bindings.yaml`
- `cowork/shared/`
- `cowork/modes/`
- `cowork/adapters/`

`ops/codex-cli/` must not be referenced from `config/runtime/runtime_manifest.yaml`.
Ordinary Cowork launch paths should continue to work without reading this
directory.

## Files

| File | Role |
| --- | --- |
| `run_schedule.sh` | Server wrapper around `codex exec`, source/article prefetch, Stage C materialization, validation, and delivery. |
| `prompts/weekday_digest.md` | Wrapper prompt template for the staged weekday daily schedule. |
| `prompts/weekday_digest_discovery.md` | Stage A prompt for `monitor_sources` shortlist generation. |
| `prompts/weekday_digest_finish.md` | Stage C prompt for strict finish draft generation. |
| `prompts/weekly_digest.md` | Non-interactive prompt for the weekly digest schedule. |
| `prompts/breaking_alert.md` | Non-interactive prompt for the hourly alert check. |
| `../../tools/source_discovery_prefetch.py` | Stage A source evidence prefetch before inner Codex starts. |
| `../../tools/shortlist_article_prefetch.py` | Stage B article/full-text prefetch for shortlisted URLs only. |
| `../../tools/stage_c_finish.py` | Deterministic Stage C materializer for current-run artifacts and digest markdown. |
| `../../tools/codex_schedule_delivery.py` | Wrapper-level delivery retry/finalization helper that invokes `telegram_send.py` and records delivery evidence. |
| `../../tools/telegram_send.py` | Low-level Telegram send and dry-run helper for the materialized digest. |

## Server Usage

From the repository root:

```bash
ops/codex-cli/run_schedule.sh weekday_digest
ops/codex-cli/run_schedule.sh weekly_digest
ops/codex-cli/run_schedule.sh breaking_alert
```

The wrapper:

- validates and loads `.env` if present;
- activates `.venv` if present;
- creates `.state/codex-runs/`;
- runs static source discovery prefetch through
  `tools/source_discovery_prefetch.py` before the inner Codex agent starts;
- passes prefetch artifact paths to the generated inner prompt;
- uses a lock directory to prevent concurrent scheduled runs;
- writes Codex JSONL events and the final message under `.state/codex-runs/`.

## Victory Digest Production-Like Run

Victory Digest is the operator label for a production-like `weekday_digest`
test run through the canonical wrapper:

```bash
ops/codex-cli/run_schedule.sh weekday_digest
```

For `weekday_digest`, the wrapper runs:

- Stage A: sandboxed source discovery and shortlist emission.
- Stage B: direct full-text collection for the current shortlist through
  `tools/shortlist_article_prefetch.py`.
- Stage C: sandboxed enrichment, digest generation, review, and delivery.

Stage A and Stage C run through `codex exec` with `workspace-write`. Stage B is
not a separate Codex agent; it is a deterministic helper call from the wrapper.
It may fetch full text only for URLs present in the current-run shortlist shard.

If Stage B fails or does not write article prefetch manifests, the wrapper writes
a synthetic article prefetch fallback so Stage C can continue with
`snippet_fallback` evidence rather than failing the whole digest.

After Stage C returns, the wrapper validates that current-run
`scrape_and_enrich` and `build_daily_digest` manifests exist for the schedule run
timestamp. A date-level digest file alone is not enough to mark Victory Digest
complete.

Stage C has a strict IO boundary. The inner Codex agent writes one compact
finish draft under `.state/codex-runs/*-finish-draft.json`; the wrapper then
runs `tools/stage_c_finish.py` to materialize `.state/enriched`,
`.state/runs`, `.state/briefs`, and `digests/{date}-daily-digest.md`.
If the draft is missing, stale, invalid, or leaks runtime paths into the digest
body, the wrapper fails before delivery.

Delivery is a wrapper-owned finalization step. `tools/codex_schedule_delivery.py`
invokes `tools/telegram_send.py`, handles retry/finalization policy, and records
delivery evidence for the scheduled run.

Post-run checks:

```bash
CODEX_RUN_SCHEDULE_SELF_TEST=1 ops/codex-cli/run_schedule.sh weekday_digest
test -s digests/YYYY-MM-DD-daily-digest.md
find .state/runs/YYYY-MM-DD -type f \( -name '*scrape_and_enrich*' -o -name '*build_daily_digest*' \) -print
find .state/codex-runs -type f -name '*-finish-draft.json' -print
python3 tools/validate_runtime_artifacts.py --check all
python3 tools/test_stage_c_finish.py
python3 tools/test_telegram_send.py
python3 tools/telegram_send.py --profile telegram_digest --date YYYY-MM-DD --dry-run < digests/YYYY-MM-DD-daily-digest.md
```

A production-like weekday run should have current-run `scrape_and_enrich` and
`build_daily_digest` manifests, `critical_findings_count = 0`, Russian digest
text, no runtime path leakage, and Telegram dry-run `parts_sent = 1`.

## Runner Dependencies

Install Python dependencies in the same environment used by scheduled jobs:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r tools/requirements.txt
python3 -m playwright install chromium
```

Verify Playwright before expecting `chrome_scrape` sources to work:

```bash
python3 -c "from playwright.sync_api import sync_playwright; print('playwright import ok')"
python3 - <<'PY'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("about:blank")
    print(page.title())
    browser.close()
PY
```

The Chromium payload is installed outside the repository in Playwright's cache.
Initial install may require network access. Scheduled runs must not attempt to
install browsers automatically.

The inner Codex agent still runs with `-s workspace-write`. Do not switch the
scheduled wrapper to `danger-full-access` to work around network access. Static
network I/O belongs in the prefetch helper; the inner agent should consume the
local JSON artifacts and apply the canonical runtime contracts.

The wrapper loads `.env` with a restricted parser, not shell `source`. Use simple
`KEY=VALUE` lines only. Single-quote any value containing spaces, parentheses,
`#`, `$`, or quotes. Malformed `.env` files fail before Codex is started, and
the wrapper reports the offending file without printing secret values.

## Secret-Safe Run Review

`.state/` remains git-ignored and local-only. Do not commit Codex JSONL event
logs, final-message transcripts, `.env` values, full Telegram Bot API URLs, or
scraped HTML/article bodies.

For launch review, write a compact tracked summary under `docs/run-reviews/`
using the template there. Record source, enrichment, digest, QA, and delivery
outcomes with sanitized status labels and redacted placeholders only. Keep raw
run evidence in local `.state/` until the operator retention window expires.

If a JSONL event log may contain a token, full Bot API URL, cookie, proxy
credential, or bulky scraped body, keep it out of tracked docs and quarantine it
locally under `.state/quarantine/` for operator review. Do not redact or rewrite
historical `.state/` logs without explicit operator approval.

Before committing review material, run the secret scan documented in
`docs/run-reviews/README.md`.

Set `CODEX_BIN` to override the Codex executable:

```bash
CODEX_BIN=/usr/local/bin/codex ops/codex-cli/run_schedule.sh weekday_digest
```

Run a local wrapper smoke check without starting Codex:

```bash
CODEX_RUN_SCHEDULE_SELF_TEST=1 ops/codex-cli/run_schedule.sh weekday_digest
```

## Runtime Guardrails

Scheduled Codex runs may write run artifacts to `.state/` and digest artifacts to
`digests/`.

Scheduled runs must not edit source-of-truth files such as `cowork/`,
`config/runtime/`, `docs/`, `tools/`, `prompts/`, `benchmark/`, `README.md`,
`AGENTS.md`, or `PLANS.md`. If a persistent fix is needed, the run should emit a
`change_request` according to `cowork/shared/change_request_policy.md`.
