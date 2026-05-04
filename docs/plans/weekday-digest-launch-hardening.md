# Weekday Digest Launch Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `weekday_digest` launchable through the canonical wrapper with safe environment loading, classified source/delivery failures, no secret leakage, aligned digest paths, and reviewable status semantics.

**Architecture:** Keep fixes small and contract-first. The launch wrapper owns startup/environment validation, source tooling owns fetch classification, Telegram tooling owns delivery redaction, and mode contracts own digest/status semantics. Do not turn this into a runner rewrite.

**Tech Stack:** Bash wrapper, Python helper scripts/tests, YAML runtime contracts/fixtures, Markdown operator docs.

---

## Source Review

This plan is based on `/Users/dvalekseev/Documents/Codex/2026-05-04-weekday-digest.md`
and the current `codex-runner-scraping-tooling` branch after source-group
corrections.

Already addressed in this branch:

- REA Group active source was replaced with `rea_group_media_releases`.
- Inman was promoted into `daily_core`.
- Offline runner artifact validation passes for current source groups.
- The REA media releases URL returned HTTP 200 in a live fetch check.

Still in scope:

- canonical launch wrapper still uses obsolete Codex CLI syntax;
- `.env.example` still shows an unquoted `HTTP_USER_AGENT` value containing
  spaces and parentheses;
- Telegram send errors can still surface secret-bearing bot API URLs;
- digest filename contract differs between runtime contract and mode prompt;
- all-snippet/fallback digest status semantics are not explicit;
- `.state/` run evidence remains ignored without a tracked retention/audit
  policy;
- stale/catch-up source behavior is not formally reported.

## Milestones

### WLH-M1. Launch Wrapper And Environment Gate

Goal: make `ops/codex-cli/run_schedule.sh weekday_digest` start with the
installed Codex CLI and fail early with readable operator errors when `.env` is
malformed.

Scope:

- `ops/codex-cli/run_schedule.sh`
- `.env.example`
- `ops/codex-cli/README.md`
- `docs/codex-cli-server-launch.md`

Dependencies:

- none.

Risks:

- local Codex desktop and server Codex CLI versions may differ;
- making `.env` parsing permissive could hide invalid secrets.

Acceptance criteria:

- wrapper no longer passes unsupported `codex exec -a never`;
- wrapper either uses current supported CLI flags or version-gated fallback;
- `.env.example` quotes `HTTP_USER_AGENT`;
- docs state that values containing spaces, parentheses, `#`, `$`, or quotes
  must be shell-quoted;
- malformed `.env` fails before runtime work starts with a message pointing to
  the offending file.

Tests/verification:

- `codex exec --help` confirms selected flags exist;
- `bash -n ops/codex-cli/run_schedule.sh`;
- add a no-network wrapper smoke check using a temporary prompt or dry command
  if feasible without starting a full digest;
- manual review that `.env.example` contains no real secrets.

Non-goals:

- do not broaden sandbox permissions by default;
- do not change schedule bindings.

### WLH-M2. Telegram Secret Redaction And Delivery Failure Classification

Goal: ensure failed Telegram delivery cannot leak bot tokens or full bot API
URLs, while preserving enough failure detail for operators.

Scope:

- `tools/telegram_send.py`
- `tools/test_telegram_send.py`
- `cowork/adapters/telegram_format.md`
- operator docs if behavior changes.

Dependencies:

- WLH-M1 for launch environment clarity.

Risks:

- over-redaction can make delivery failures hard to debug;
- live Telegram delivery still depends on network and valid rotated secrets.

Acceptance criteria:

- any exception containing `https://api.telegram.org/bot...` is sanitized before
  it reaches stdout/stderr JSON, event logs, or delivery metadata;
- errors include classified fields such as `delivery_failed_dns`,
  `delivery_failed_http`, `delivery_failed_api`, or `delivery_failed_unknown`;
- `TELEGRAM_MESSAGE_THREAD_ID=` empty string behavior is documented or
  normalized as unset;
- tests simulate secret-bearing Telegram request exceptions without using real
  tokens.

Tests/verification:

- `python3 tools/test_telegram_send.py`;
- targeted test asserts token and full bot API URL are absent from error output;
- `python3 tools/telegram_send.py --profile telegram_digest --date 2026-05-04 --dry-run < <sample digest>` with a tracked or temporary sample.

Non-goals:

- do not run live Telegram delivery in this milestone;
- do not change Telegram parse mode.

### WLH-M3. Digest Path Contract Alignment

Goal: choose one canonical weekday digest markdown filename and align producers,
contracts, fixtures, and docs.

Scope:

- `cowork/modes/build_daily_digest.md`
- `config/runtime/mode-contracts/build_daily_digest_rendering.yaml`
- `config/runtime/mode-fixtures/build_daily_digest_*.yaml`
- `config/runtime/regression-fixtures/*.yaml`
- `config/runtime/legacy-export-fixtures/*.yaml`
- docs that mention daily digest paths.

Dependencies:

- none, but implement after WLH-M1 if wrapper smoke output depends on digest
  paths.

Risks:

- changing the canonical filename can break downstream readers and historical
  references;
- legacy digest archives use multiple naming patterns.

Acceptance criteria:

- one canonical path template is stated in both mode prompt and runtime
  contract;
- `daily_brief.markdown_path` must point to that canonical path for new runs;
- legacy fixture references are either updated or explicitly marked as legacy;
- review/fanout/weekly consumers have compatible expectations.

Tests/verification:

- `rg -n "daily-digest|daily.md|markdown_path" cowork config docs tools`;
- `python3 tools/validate_runtime_artifacts.py --check all`;
- add/update fixture where `daily_brief.markdown_path` matches the chosen path.

Non-goals:

- do not rename historical digest files unless a compatibility decision
  explicitly requires it.

### WLH-M4. Source DNS And Fetch Failure Classification

Goal: separate global runner/network failures from source-level outcomes so
`monitor_sources` does not produce clean-looking empty outputs after DNS failure.

Scope:

- `tools/rss_fetch.py`
- `tools/test_rss_fetch.py`
- `cowork/modes/monitor_sources.md`
- `config/runtime/mode-contracts/monitor_sources.yaml`
- `config/runtime/mode-fixtures/` or `config/runtime/regression-fixtures/`

Dependencies:

- WLH-M1, because launch environment affects DNS/network behavior.

Risks:

- temporary DNS outages can look like code regressions;
- source-specific timeouts should not be collapsed into global environment
  failures.

Acceptance criteria:

- global DNS failure across all fetchable daily sources is classified as an
  environment/run failure, not as empty source output;
- individual source failures remain source-level outcomes such as `timeout`,
  `blocked`, `selector_miss`, or `rate_limited`;
- current known transient `costar_homes` timeout remains a source-level
  soft-fail unless other sources also fail at resolver level;
- source runner output gives enough information for `monitor_sources` to emit a
  change request or partial manifest without web fallback pretending to be
  canonical.

Tests/verification:

- add deterministic unit test that simulates `NameResolutionError` for all
  batch sources and expects global DNS classification;
- add deterministic unit test that simulates one source timeout and expects a
  source-level soft fail;
- `python3 tools/test_rss_fetch.py`;
- `python3 tools/validate_runtime_artifacts.py --check all`.

Non-goals:

- do not add web-search fallback as a permanent source discovery path;
- do not require live network in deterministic tests.

### WLH-M5. Enrichment Evidence And All-Snippet Gate

Goal: define what happens when `scrape_and_enrich` produces only
`snippet_fallback` records and no full article evidence.

Scope:

- `cowork/modes/scrape_and_enrich.md`
- `config/runtime/mode-contracts/scrape_and_enrich_output.yaml`
- `config/runtime/mode-contracts/build_daily_digest_selection.yaml`
- `cowork/modes/build_daily_digest.md`
- `config/runtime/mode-fixtures/`

Dependencies:

- WLH-M4, because DNS/global fetch failure can cause all-snippet outputs.

Risks:

- requiring full text for every item can violate full-text/context boundaries;
- allowing all-snippet digests can make weak evidence look production-ready.

Acceptance criteria:

- all enriched records with `body_status=snippet_fallback` must cause one of:
  `blocked_before_digest`, `partial_digest`, or `non_canonical_digest`;
- chosen behavior is represented in contracts and fixtures;
- daily digest mode still does not read full article bodies or `.state/articles/`;
- each selected item keeps durable source URLs and compact evidence notes.

Tests/verification:

- add/update fixture with all `snippet_fallback` enriched records;
- validate expected downstream behavior;
- `python3 tools/validate_runtime_artifacts.py --check all`.

Non-goals:

- do not expand full article text into `build_daily_digest`;
- do not fetch bodies for non-shortlisted items.

### WLH-M6. Run Status And Operator Report Semantics

Goal: make final run reports distinguish discovery, enrichment, digest
generation, validation, and delivery instead of collapsing mixed outcomes into
one success label.

Scope:

- `config/runtime/state_schemas.yaml`
- `cowork/shared/contracts.md` if present/needed
- `cowork/modes/build_daily_digest.md`
- `cowork/modes/review_digest.md`
- `ops/codex-cli/prompts/weekday_digest.md`
- relevant mode fixtures.

Dependencies:

- WLH-M4 and WLH-M5.

Risks:

- changing status enums can break consumers;
- leaving status as-is can make partial upstream execution look successful.

Acceptance criteria:

- compatibility decision is recorded before changing any status enum;
- final operator report has separate fields for source discovery, enrichment,
  digest generation, QA/review, and Telegram delivery;
- `completed` downstream digest with `partial` upstream inputs is either
  allowed with warnings or converted to a clear partial/non-canonical status;
- fixtures cover mixed partial/completed runs.

Tests/verification:

- schema validation for sample manifests;
- fixture validation for mixed-status run;
- `python3 tools/validate_runtime_artifacts.py --check all`.

Non-goals:

- do not rewrite historical run manifests.

### WLH-M7. Evidence Retention And Secret-Safe Run Review

Goal: preserve enough evidence for launch review while keeping `.state/`
git-ignored and secret-safe.

Scope:

- new tracked run-review summary location, likely `docs/run-reviews/`
- `.gitignore` only if retention policy changes;
- `ops/codex-cli/README.md`
- optional validation script/test for secret patterns.

Dependencies:

- WLH-M2 for redaction behavior.

Risks:

- storing too much run evidence can leak secrets or create large diffs;
- storing too little makes launch failures impossible to audit.

Acceptance criteria:

- tracked summary format records source/delivery/status outcomes without raw
  secrets, full bot API URLs, or bulky HTML bodies;
- `.state/` remains ignored unless explicitly reversed by operator decision;
- local retention/quarantine guidance exists for unsafe JSONL event logs;
- secret scan pattern is documented or automated.

Tests/verification:

- run a secret-pattern scan against tracked files;
- validate that new docs use redacted placeholders only;
- `git diff --check`.

Non-goals:

- do not commit historical `.state/` artifacts;
- do not redact local historical logs unless explicitly approved.

### WLH-M8. End-To-End Recovery Dry Run

Goal: prove the hardened path works from canonical wrapper command through
artifacts and delivery reporting, or identify a single external blocker.

Scope:

- generated `.state/` artifacts from one new run;
- wrapper output and event log;
- generated digest markdown and daily brief;
- Telegram dry-run and, only if approved, live delivery.

Dependencies:

- WLH-M1 through WLH-M7.

Risks:

- live sources may legitimately have no new content;
- Telegram may remain blocked by network or invalid credentials.

Acceptance criteria:

- `ops/codex-cli/run_schedule.sh weekday_digest` reaches the agent without
  `.env` parse errors or unsupported Codex flags;
- source discovery does not fail globally at DNS;
- digest path matches the chosen contract;
- if enrichment is all-snippet, the run is marked according to WLH-M5/WLH-M6;
- delivery either sends message parts or records sanitized classified failure;
- final operator report states production-ready, partial, or externally blocked.

Tests/verification:

- run canonical wrapper command;
- run JSON/schema checks for generated artifacts;
- run digest body checks for `.state/`, full run IDs, and operator notes;
- run Telegram dry-run;
- run secret scan over new event log and tracked summary.

Non-goals:

- do not use web-search fallback to satisfy source discovery unless explicitly
  approved and labeled non-canonical.

## Coverage Matrix

| Problem | Milestone(s) |
| --- | --- |
| R20260504-P1 `.env` parse failure | WLH-M1 |
| R20260504-P2 obsolete `codex exec -a never` | WLH-M1 |
| R20260504-P3 Codex session permission/sandbox issue | WLH-M1, WLH-M8 |
| R20260504-P4 source DNS failures | WLH-M4, WLH-M8 |
| R20260504-P5 no full article text | WLH-M5 |
| R20260504-P6 web fallback non-canonical artifacts | WLH-M4, WLH-M5, WLH-M6 |
| R20260504-P7 Telegram delivery failed | WLH-M2, WLH-M8 |
| R20260504-P8 Telegram token leaked in log | WLH-M2, WLH-M7 |
| R20260504-P9 fallback provenance durability | WLH-M7 |
| R20260504-P10 mixed partial/completed statuses | WLH-M6 |
| R20260504-P11 initial mode-limited build failure | WLH-M6, WLH-M8 |
| R20260504-P12 `.env`/`.state` drift and secret risk | WLH-M1, WLH-M2, WLH-M7 |
| R20260504-P13 digest markdown path drift | WLH-M3 |
| R20260504-P14 ignored `.state` reviewability | WLH-M7 |
| R20260504-P15 freshness/catch-up visibility | WLH-M6, WLH-M8 |

## Implementation Discipline

- Implement one milestone at a time.
- Before each milestone, restate its acceptance criteria.
- Commit after each milestone once validation passes.
- Do not run live Telegram delivery until WLH-M2 is implemented and the token
  rotation/log-retention decision is explicit.
- Do not modify source groups again unless a milestone-specific validation
  failure proves it is required.

