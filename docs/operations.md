# Operations

This document covers minimum dry-run readiness for the refactored weekday and weekly runner. It does not claim full runtime rebuild completion or production cutover.

## Offline Self-Tests

```bash
runner/run.sh --self-test weekday
runner/run.sh --self-test weekly
python3 runner/tools/validate_runtime.py --check all
python3 -m pytest runner/tests -q
```

## Offline Dry-Run

```bash
runner/run.sh --dry-run weekday
runner/run.sh --dry-run weekly
```

The offline dry-run validates runtime wiring and writes a local `offline_wiring_ready` report under `.state/refactor-dry-runs/`. It does not invoke live Codex, live source fetches, or Telegram delivery. In the minimum facade, the new `runtime/prompts/` files are validated as contracts but live runs still delegate to the existing legacy prompt wrapper.

## Live Handoff

```bash
runner/run.sh weekday
runner/run.sh weekly
```

The live commands delegate to the existing `ops/codex-cli/run_schedule.sh` wrapper using `weekday_digest` and `weekly_digest`. Use live commands only after offline self-tests and dry-runs pass.

## Boundaries

- New runner supports only `weekday` and `weekly`.
- `breaking_alert` remains out of scope for the refactored runner.
- Legacy `config/runtime/`, `cowork/`, `tools/`, and `ops/codex-cli/` remain in place for this minimum.
- `runtime_prompts_consumed_by_live_run` is expected to be `false` in offline reports until the full runtime migration replaces legacy prompt consumption.
- Full hard rebuild cleanup remains separate planned work.
