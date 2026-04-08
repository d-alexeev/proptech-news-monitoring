# Launch, Rerun, and Dry-Run Reference

## Purpose

Этот документ описывает current-state способы запуска для runtime-дизайна,
зафиксированного в [`config/runtime/runtime_manifest.yaml`](../config/runtime/runtime_manifest.yaml).

Важно:

- этот репозиторий остаётся source-of-truth для runtime layers;
- фактический runner может исполняться вне этого репозитория;
- launch mapping должен брать schedules, source groups и mode boundaries из
  canonical runtime layer, а не из legacy монолитного пути.

## Regular Schedules

Canonical schedule bindings описаны в
[`config/runtime/schedule_bindings.yaml`](../config/runtime/schedule_bindings.yaml).

### `weekday_digest`

- Enabled: `true`
- Days: `MON, TUE, WED, THU, FRI`
- Time: `09:00`
- Source groups: `daily_core`
- Delivery profile: `telegram_digest`

Typical runtime path:

1. `monitor_sources`
2. `scrape_and_enrich`
3. `build_daily_digest`
4. optional `review_digest`

### `weekly_digest`

- Enabled: `true`
- Days: `FRI`
- Time: `17:00`
- Source groups: `daily_core`, `weekly_context`
- Delivery profile: `telegram_weekly_digest`

Typical runtime path:

1. source-facing pass over weekly window inputs
2. `build_weekly_digest`
3. optional `review_digest`

### `breaking_alert`

- Enabled: `true`
- Check every: `60 minutes`
- Source groups: `daily_core`, `weekly_context`
- Delivery profile: `telegram_alert`

Typical runtime path:

1. `monitor_sources`
2. `scrape_and_enrich`
3. `breaking_alert`

## Manual Reruns

Manual rerun должен использовать тот же canonical runtime layer, но писать новый
`run_id` и новый `run_manifest`.

### Full schedule rerun

Использовать, когда нужно повторить один из canonical schedule paths:

- `weekday_digest`
- `weekly_digest`
- `breaking_alert`

Rules:

- reuse the same schedule binding and source-group scope;
- do not overwrite plan docs or prompt files from the runner environment;
- write new state artifacts instead of silently mutating prior run output;
- if rerun surfaces a persistent runtime issue, emit `change_request`.

### Mode-limited rerun

Разрешён только если все upstream compact artifacts уже существуют.

Typical cases:

- rerun `review_digest` for an already-built digest;
- rerun `stakeholder_fanout` for a different stakeholder profile;
- rerun `build_weekly_digest` when current-week `daily_brief` artifacts are already present.

Mode-limited rerun must not backfill missing upstream layers implicitly.

## Downstream-Only Modes

Следующие режимы являются downstream-only и не должны повторно запускать source
discovery или full-text fetch:

- `review_digest`
- `stakeholder_fanout`

`build_weekly_digest` не является purely downstream fanout mode, но он работает
по compact daily/weekly briefs и не требует raw source universe или article
bodies.

## Regression and Parity Dry-Runs

Canonical dry-run and pre-cutover validation references:

- [`config/runtime/regression_harness.yaml`](../config/runtime/regression_harness.yaml)
- [`config/runtime/regression-fixtures/smoke_subsets.yaml`](../config/runtime/regression-fixtures/smoke_subsets.yaml)
- [`config/runtime/regression-fixtures/recent_week_parity.yaml`](../config/runtime/regression-fixtures/recent_week_parity.yaml)
- [`config/runtime/regression-fixtures/cutover_dry_run.yaml`](../config/runtime/regression-fixtures/cutover_dry_run.yaml)

### Smoke subsets

Used for focused regression checks on:

- `JTBD-06`
- `JTBD-07`
- `JTBD-08`
- `JTBD-09`

### Recent-week parity review

Used to compare current architecture outputs with a recent real project window:

- recent daily window
- recent weekly window

### Cutover dry-run

Used before cutover to confirm:

- smoke subsets are green;
- parity review is green;
- rollback path is rehearsed;
- default decision on uncertainty remains `no_go`.

## Runner Boundary

Этот репозиторий не фиксирует единственный CLI или orchestration shell для
фактического запуска.

Canonical requirement instead is:

- map launch behavior to `schedule_bindings.yaml`,
- load the current mode prompts from [`cowork/`](../cowork),
- respect the state layout and contracts from [`config/runtime/`](../config/runtime),
- route persistent fixes back through `change_request` and Codex-side git workflow.

If a runner-specific command surface exists elsewhere, it should be treated as an
execution wrapper around this source-of-truth layer, not as a replacement for it.
