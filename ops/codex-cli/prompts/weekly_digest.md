# Codex CLI Launch Mode: weekly_digest

You are running non-interactively through `codex exec` on a server.

This is an external launch wrapper for the existing PropTech News Monitoring
runtime. It is not a request to change the repository's canonical runtime
source files.

## Schedule Binding

Run `weekly_digest` exactly as defined in
`config/runtime/schedule_bindings.yaml`.

Expected mode path:

1. source-facing pass over weekly window inputs when required by existing
   schedule and available compact artifacts
2. `build_weekly_digest`
3. optional `review_digest`

Source groups: use the schedule binding's source groups, currently `daily_core`
and `weekly_context`.
Delivery profile: use the schedule binding's delivery profile, currently
`telegram_weekly_digest`.

## Required Runtime Context

Read only the compact canonical runtime files needed for this run:

- `AGENTS.md`
- `config/runtime/runtime_manifest.yaml`
- `config/runtime/schedule_bindings.yaml`
- relevant files from `config/runtime/source-groups/`
- relevant contracts from `config/runtime/mode-contracts/`
- relevant prompts from `cowork/shared/` and `cowork/modes/`
- source adapters from `cowork/adapters/` only when required by selected sources
- existing compact daily and weekly briefs from `.state/`
- `tools/README.md` only if needed to use helper scripts

Do not read full article bodies or the full markdown digest archive unless a
canonical weekly contract explicitly permits a compact reference.

## Write Boundaries

Allowed writes:

- `.state/` run artifacts
- `digests/` digest artifacts
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

If Telegram environment variables are configured, send the completed digest via
`tools/telegram_send.py --profile telegram_weekly_digest`.

If delivery is not configured or fails, preserve the digest and run artifacts and
report the delivery status in the final response.

## Final Response

Return a concise run report with:

- run id or timestamp
- artifacts written
- delivery status
- validation performed
- incomplete items or change requests

