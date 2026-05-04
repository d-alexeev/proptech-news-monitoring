# Source Discovery Runner Prefetch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make scheduled `weekday_digest` source discovery use deterministic runner-side network fetch artifacts instead of requiring the inner `codex exec` agent sandbox to have DNS/network access.

**Architecture:** Keep the inner agent sandboxed for repo edits and reasoning. Move static source I/O into a narrow runner-owned prefetch step that reads source-group config, runs `tools/rss_fetch.py`, writes local `.state/codex-runs/` artifacts, and passes those artifact paths to the mode prompt. Browser-backed `chrome_scrape` remains a separate partial/non-canonical path until a headless browser runner exists.

**Tech Stack:** Bash wrapper, Python helper scripts/tests, YAML source-group config, JSON run artifacts, Markdown runtime prompts/contracts.

---

## Root Cause Evidence

Observed on 2026-05-04:

- `ops/codex-cli/run_schedule.sh weekday_digest` reached the inner agent and exited `0`.
- Inside the inner `codex exec -s workspace-write` run, DNS failed for `example.com` and all fetchable `daily_core` sources.
- The same machine, outside sandbox, resolved `example.com` and returned HTTP 200.
- A direct out-of-sandbox `tools/rss_fetch.py` batch showed source discovery is not globally broken:
  - `aim_group_real_estate_intelligence`: RSS parsed, 30 items.
  - `mike_delprete`: static HTML fetched.
  - `zillow_newsroom`: RSS parsed, 5 items.
  - `costar_homes`: source-level `timeout`.
  - `redfin_news`: RSS parsed, 6 items.
  - `rea_group_media_releases`: static HTML fetched.
  - `inman_tech_innovation`: RSS parsed, 18 items.
  - `rightmove_plc`: source-level DNS failure in local DNS at the time of test.
- A nested `codex exec -s danger-full-access` probe was rejected as too broad, so broad unsandboxing must not be the default remediation.

Conclusion: the blocker is the boundary between scheduled inner agent sandboxing and network I/O, not the active REA/Inman source configuration.

## Milestones

### SD-M1. Runner Static Prefetch Helper

Goal: add a deterministic helper that performs static source fetches before the inner agent starts.

Scope:

- `tools/source_discovery_prefetch.py`
- `tools/test_source_discovery_prefetch.py`
- `tools/README.md`

Likely behavior:

- read `config/runtime/schedule_bindings.yaml` for a schedule id;
- read configured source groups, initially `daily_core`;
- build fetch specs for `rss`, `html_scrape`, and `itunes_api`;
- skip `chrome_scrape` with explicit metadata rather than pretending it was fetched;
- run `tools/rss_fetch.py --stdin --pretty`;
- run DNS preflight for `example.com` and configured fetchable hosts;
- write JSON artifacts under `.state/codex-runs/`;
- print a compact JSON summary with artifact paths.

Risks:

- duplicating source config parsing outside the mode prompt can drift from runtime contracts;
- large HTML bodies remain local artifacts and must not become prompt context wholesale.

Acceptance criteria:

- helper writes fetch result and DNS check artifacts without writing raw/shortlist shards;
- helper reports fetchable source count, attempted count, success count, and skipped browser source count;
- helper preserves `global_dns_resolution_failure` as a runner/network blocker;
- helper preserves mixed source-level failures as partial discovery evidence;
- helper does not log secrets or `.env` values.

Verification:

- unit tests with mocked `rss_fetch.py` subprocess output for success, partial, and global DNS failure;
- `python3 tools/test_source_discovery_prefetch.py`;
- `python3 tools/validate_runtime_artifacts.py --check all`.

Non-goals:

- do not implement browser automation here;
- do not emit canonical raw/shortlist shards from the helper.

### SD-M2. Wrapper Integration

Goal: make `ops/codex-cli/run_schedule.sh weekday_digest` run static prefetch first and pass artifact paths to the inner prompt.

Scope:

- `ops/codex-cli/run_schedule.sh`
- `ops/codex-cli/README.md`
- `tools/test_codex_cli_run_schedule.py`

Acceptance criteria:

- wrapper has a self-test path that verifies prefetch wiring without live network;
- wrapper creates a run-specific prompt preamble or environment file pointing to prefetch artifacts;
- inner `codex exec` remains `-s workspace-write` by default;
- if prefetch itself has global DNS failure, the inner agent receives the artifact and can produce a failed run report without re-fetching;
- no `danger-full-access` default is introduced.

Verification:

- `CODEX_RUN_SCHEDULE_SELF_TEST=1 ops/codex-cli/run_schedule.sh weekday_digest`;
- wrapper tests cover default sandbox staying `workspace-write`;
- wrapper tests cover prefetch disabled/enabled behavior if an escape hatch is needed.

Non-goals:

- do not require operator approval during cron execution;
- do not broaden sandbox permissions by default.

### SD-M3. Prompt And Contract Consumption

Goal: teach scheduled `weekday_digest` / `monitor_sources` to consume runner prefetch artifacts as canonical static source evidence.

Scope:

- `ops/codex-cli/prompts/weekday_digest.md`
- `cowork/modes/monitor_sources.md`
- `config/runtime/mode-contracts/monitor_sources.yaml`
- relevant fixtures in `config/runtime/mode-fixtures/`

Acceptance criteria:

- when runner prefetch artifacts are present, `monitor_sources` uses them instead of re-running static network fetches inside the inner sandbox;
- fetch result artifacts are evidence, not raw prompt context; large `body` fields are referenced and summarized under adapter rules;
- browser sources remain explicitly `not_attempted` unless a browser artifact exists;
- mixed static source failures can proceed as partial discovery when enough configured sources succeeded.

Verification:

- fixture for prefetch success with source-level failures;
- fixture for prefetch global DNS blocker;
- `python3 tools/test_validate_runtime_artifacts.py`;
- `python3 tools/validate_runtime_artifacts.py --check all`.

Non-goals:

- do not add web-search fallback;
- do not pass full article text into `monitor_sources` or `build_daily_digest`.

### SD-M4. Recovery Run

Goal: prove the revised path changes the failure mode from global sandbox DNS block to source-level partial discovery.

Scope:

- generated `.state/` artifacts only;
- tracked run review under `docs/run-reviews/`.

Acceptance criteria:

- static prefetch runs outside the inner agent sandbox and writes local artifacts;
- inner agent reads prefetch artifacts and does not attempt duplicate static network fetches;
- source discovery is `partial` if only `costar_homes`, `rightmove_plc`, or browser sources fail while other configured sources succeeded;
- digest is either generated as `partial_digest` / `non_canonical_digest`, or blocked with a stage-specific reason unrelated to global DNS;
- Telegram delivery is sent or records a sanitized classified failure.

Verification:

- run canonical wrapper command;
- parse generated JSON artifacts;
- run digest body checks if a digest exists;
- run documented secret scan against tracked run review and event logs.

Non-goals:

- do not claim production-ready while `chrome_scrape` lacks a non-interactive browser runner.

## Coverage Matrix

| Problem | Milestone |
| --- | --- |
| Inner `codex exec` sandbox cannot resolve DNS | SD-M1, SD-M2 |
| Source adapters incorrectly blamed for global DNS | SD-M1, SD-M4 |
| Need to keep inner agent sandboxed | SD-M2 |
| Existing `daily_core` static sources can mostly fetch outside sandbox | SD-M1, SD-M4 |
| Browser sources still lack server runner | SD-M1, SD-M3, SD-M4 |
| Large listing HTML must not become full prompt context | SD-M1, SD-M3 |
| Run evidence must remain reviewable and secret-safe | SD-M4 |

## Current Recommendation

Implement SD-M1 through SD-M3 before re-running full `weekday_digest`.
Do not use `danger-full-access` as the default scheduled runner fix.
