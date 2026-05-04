# Codex CLI Launch Mode: weekday_digest

You are running non-interactively through `codex exec` on a server.

This is an external launch wrapper for the existing PropTech News Monitoring
runtime. It is not a request to change the repository's canonical runtime
source files.

## Schedule Binding

Run `weekday_digest` exactly as defined in
`config/runtime/schedule_bindings.yaml`.

Expected mode path:

1. `monitor_sources`
2. `scrape_and_enrich`
3. `build_daily_digest`
4. optional `review_digest`

Source groups: use the schedule binding's source groups, currently `daily_core`.
Delivery profile: use the schedule binding's delivery profile, currently
`telegram_digest`.

## Required Runtime Context

Read only the compact canonical runtime files needed for this run:

- `AGENTS.md`
- `config/runtime/runtime_manifest.yaml`
- `config/runtime/schedule_bindings.yaml`
- relevant files from `config/runtime/source-groups/`
- relevant contracts from `config/runtime/mode-contracts/`
- relevant prompts from `cowork/shared/` and `cowork/modes/`
- source adapters from `cowork/adapters/` only when required by selected sources
- `tools/README.md` only if needed to use helper scripts

Avoid loading broad human reference docs unless blocked and necessary.

## Runner Source Prefetch

When this prompt contains a "Runner Source Discovery Prefetch" preamble, treat
the listed prefetch summary and fetch result JSON files as the static source
runner output for `monitor_sources`.

Do not repeat static RSS/HTTP network fetches from inside this `codex exec`
sandbox for sources already represented in the prefetch artifacts. Use the
artifact paths as local evidence references. For large HTTP listing bodies,
extract only adapter-relevant compact discovery facts; do not paste full listing
HTML into run artifacts or reasoning notes.

Configured `chrome_scrape` sources are covered only when the prefetch summary
contains `browser_result_path` and the referenced browser artifact exists. Use
that browser artifact as compact listing/snippet evidence only. If it is absent
or reports `browser_runtime_unavailable`, mark those browser sources as
`not_attempted`.

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
`tools/telegram_send.py --profile telegram_digest`.

If delivery is not configured or fails, preserve the digest and run artifacts and
report the delivery status in the final response.

## Final Response

Return a concise run report with:

- run id or timestamp
- artifacts written
- source discovery status, including whether configured source discovery was canonical and complete
- enrichment status, including evidence completeness and any downstream digest gate
- digest generation status, including generated/blocked and canonical_digest/partial_digest/non_canonical_digest
- QA/review status, including validated/skipped and warning/critical counts when available
- Telegram delivery status, including delivered/dry_run/not_configured/classified failure
- incomplete items or change requests

Do not use a single "success" or "completed" label for the whole run when stages
had mixed outcomes. Keep the stable mode-level `run_manifest.status` values, but
build the final operator report from the stage fields in `run_manifest.operator_report`
and any Telegram send report.

If `build_daily_digest` completed after partial source discovery or partial
enrichment, report the digest as generated but mark overall readiness as
`partial` or `non_canonical`; include a warning that it is not production-clean.
