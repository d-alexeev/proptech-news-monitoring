# Codex CLI Launch Mode: breaking_alert

You are running non-interactively through `codex exec` on a server.

This is an external launch wrapper for the existing PropTech News Monitoring
runtime. It is not a request to change the repository's canonical runtime
source files.

## Schedule Binding

Run `breaking_alert` exactly as defined in
`config/runtime/schedule_bindings.yaml`.

Expected mode path:

1. `monitor_sources`
2. `scrape_and_enrich`
3. `breaking_alert`

Source groups: use the schedule binding's source groups, currently `daily_core`
and `weekly_context`.
Delivery profile: use the schedule binding's delivery profile, currently
`telegram_alert`.

## Required Runtime Context

Read only the compact canonical runtime files needed for this run:

- `AGENTS.md`
- `config/runtime/runtime_manifest.yaml`
- `config/runtime/schedule_bindings.yaml`
- relevant files from `config/runtime/source-groups/`
- relevant contracts from `config/runtime/mode-contracts/`
- relevant prompts from `cowork/shared/` and `cowork/modes/`
- source adapters from `cowork/adapters/` only when required by selected sources
- recent compact story briefs and enriched items from `.state/`
- `tools/README.md` only if needed to use helper scripts

Do not read full article bodies outside `scrape_and_enrich`.

## Write Boundaries

Allowed writes:

- `.state/` run artifacts
- alert payload artifacts when applicable
- temporary logs or scratch files under `.state/codex-runs/`

Forbidden writes during this scheduled run:

- `cowork/`
- `config/runtime/`
- `docs/`
- `tools/`
- `prompts/`
- `benchmark/`
- `README.md`
- `AGENTS.md`
- `PLANS.md`
- git history or branches

If you discover a persistent runtime issue, emit a `change_request` artifact
according to `cowork/shared/change_request_policy.md` instead of editing runtime
source files.

## Delivery

If a true breaking alert exists and Telegram environment variables are
configured, send it via `tools/telegram_send.py --profile telegram_alert`.

If there is no true breaking alert, do not send a message. Preserve run artifacts
and report `no_alert` in the final response.

## Final Response

Return a concise run report with:

- run id or timestamp
- alert status: `sent`, `no_alert`, or `blocked`
- artifacts written
- delivery status
- validation performed
- incomplete items or change requests

