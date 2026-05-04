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
- uses a lock directory to prevent concurrent scheduled runs;
- writes Codex JSONL events and the final message under `.state/codex-runs/`.

Because `.env` is sourced by Bash, quote any value containing spaces,
parentheses, `#`, `$`, or quotes. Malformed `.env` files fail before Codex is
started, and the wrapper reports the offending file without printing secret
values.

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
