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
| `run_schedule.sh` | Server wrapper around `codex exec`. |
| `prompts/weekday_digest.md` | Non-interactive prompt for the weekday daily schedule. |
| `prompts/weekly_digest.md` | Non-interactive prompt for the weekly digest schedule. |
| `prompts/breaking_alert.md` | Non-interactive prompt for the hourly alert check. |

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
