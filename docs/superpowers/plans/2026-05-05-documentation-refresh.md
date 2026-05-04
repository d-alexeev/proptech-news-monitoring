# Documentation Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring project documentation back in sync with the last 100 commits, especially the Codex scheduled weekday digest runner, staged scraping/enrichment pipeline, Russian Telegram digest contract, and benchmark updates.

**Architecture:** Treat docs as a layered operator map: root `README.md` explains the current system at a glance, `docs/` contains operational and architecture runbooks, and folder READMEs explain local tooling. Preserve historical plan docs as traceability, but do not make old plans the primary way to understand the current repo.

**Tech Stack:** Markdown documentation, Git history review, runtime YAML contracts, Bash/Python helper references, no runtime code changes.

---

## Last 100 Commits: Change Summary

The last 100 commits changed the repo in these major groups:

| Area | Representative commits | What changed |
| --- | --- | --- |
| Codex scheduled runner | `e4206aa`, `36f70aa`, `2e74cdd`, `2f6de74` | Added `ops/codex-cli/run_schedule.sh`, `.env` loading guard, staged weekday wrapper, server launch docs, lock/run artifact handling. |
| Source discovery prefetch | `ed0d3cb`, `5f61e7e`, `07eaf3a`, `4392533` | Added deterministic static source prefetch before inner Codex, source DNS/fetch classification, recovery run evidence. |
| Browser runner | `a13e2e2`, `d24cc0f`, `4241466`, `2279db6` | Added Playwright-backed `tools/browser_fetch.py`, integrated browser evidence into source prefetch, documented browser dependency. |
| Stage B article/full-text collection | `f3ac895`, `9825dbd`, `ca3e86b`, `77cbf7d`, `b32ee55` | Added `article_fetch.py`, shortlist article prefetch, Inman visible paywall text handling, article status/lead image metadata. |
| Deterministic Stage C | `f52fb50`, `9e3ad8f`, `19eade1`, `f223046`, `0be968f`, `b814ee6` | Added strict finish draft contract and `tools/stage_c_finish.py` materializer for current-run artifacts. |
| Russian Telegram digest | `7c8a0a4`, `7f6005f`, `aaa7be5`, `061c8cf`, `9548253` | Added Russian text gate in Stage C and Telegram sender, rejected English editorial prose. |
| Compact Telegram template and preview | `4d20df9`, `5cb1a50`, `536a4b6`, `961251b`, `8de7530`, `a6c782b` | Added fixed compact Telegram template, hard length/template gates, `lead_image`, and Telegram large link preview dry-run support. |
| Runtime validation | `31e8536`, `0f6e007`, `a57a7a8`, `14d6ae2` | Added `validate_runtime_artifacts.py`, fixtures, runner integration map, change-request fixture checks. |
| Plans/run reviews | multiple plan, record, and document commits | Added many implementation plans and run reviews; some are now historical, not primary docs. |
| Benchmarks | `3cd58b2` through `3c9cbc8` | Added LLM judge contracts, request retrieval/synthesis/article synthesis benchmark datasets and runner support. |

## Documentation Gaps Found

| Gap | Current evidence | Required update |
| --- | --- | --- |
| Root `README.md` still frames runner as external/optional and does not make the staged Codex weekday wrapper obvious. | `README.md` has canonical runtime overview but no quick operator path for `ops/codex-cli/run_schedule.sh weekday_digest`. | Add a "Current Operator Path" section with staged weekday flow, install/test commands, and pointers to run reviews. |
| `docs/cowork-onboarding.md` is outdated for browser/source runner setup. | It says `Claude in Chrome MCP` is optional for `chrome_scrape`; current scheduled runner uses Playwright `browser_fetch.py`. It also omits `python3 -m playwright install chromium`. | Replace Chrome MCP language with Playwright runner setup and keep Browser Use/Chrome as manual debug only. |
| `tools/README.md` has stale source prefetch wording. | It says configured `chrome_scrape` sources are `not_attempted` until a browser runner exists. | Update `source_discovery_prefetch.py` section to say Playwright browser result is attempted when dependency is available. |
| `ops/codex-cli/README.md` is mostly current but missing explicit file inventory for staged weekday prompts. | File table omits `weekday_digest_discovery.md` and `weekday_digest_finish.md`; wrapper details are in prose. | Add staged weekday file table and post-run verification commands. |
| `docs/codex-cli-server-launch.md` still describes a simpler monolithic `run_schedule -> codex exec` architecture. | Architecture diagram lacks Stage A/B/C and deterministic materializer. | Update architecture diagram and smoke test section. |
| `benchmark/README.md` does not reflect last 100 benchmark commits. | It lists request retrieval but not request synthesis/article synthesis LLM judge additions. | Add current benchmark matrix and runner command. |
| Documentation index does not separate canonical docs from historical plans strongly enough. | Many docs/plans are implementation history; root README does not say which docs are operator-critical. | Add a concise "Documentation Map" in root README and avoid making archived plans primary reading. |
| Latest compact Telegram template contract is not easy to find from root docs. | Contract is in mode prompt/YAML and plan docs. | Add root/ops pointers to `build_daily_digest` template, Russian-only gate, one-message TG dry-run. |

## File Structure

| File | Responsibility in this documentation refresh |
| --- | --- |
| `README.md` | Primary repo entry point: current runtime, operator path, staged weekday flow, documentation map. |
| `docs/cowork-onboarding.md` | Human/Cowork onboarding and new-machine setup; must mention Playwright and scheduled wrapper. |
| `ops/codex-cli/README.md` | Codex scheduled runner operator runbook; should be the canonical wrapper usage doc. |
| `docs/codex-cli-server-launch.md` | Server/systemd/cron deployment guide; should match staged wrapper architecture. |
| `tools/README.md` | Tool inventory and helper contracts; remove stale "browser runner not available" wording. |
| `benchmark/README.md` | Benchmark suite overview; include LLM judge and request synthesis/article synthesis datasets. |
| `docs/run-reviews/README.md` | Optional: ensure run review expectations match current production-like weekday run evidence. |
| `PLANS.md` | Add one active documentation-refresh row while implementation is in progress, then mark completed after merge. |

## Milestones

| Milestone | Goal | Scope | Risks | Acceptance Criteria | Verification | Non-Goals |
| --- | --- | --- | --- | --- | --- | --- |
| DOC-M1 | Establish current docs baseline | Inspect last 100 commits and current docs | Over-documenting historical plan details | Plan maps all major last-100 changes to docs | `git log --oneline -100`; `rg` checks listed below | No doc edits beyond plan/index |
| DOC-M2 | Update primary entry points | `README.md`, `docs/cowork-onboarding.md` | Root README becomes too long | New operator can see current scheduled weekday path and setup in under 5 minutes | Markdown review; command references exist | No runtime behavior changes |
| DOC-M3 | Update runner/tool runbooks | `ops/codex-cli/README.md`, `docs/codex-cli-server-launch.md`, `tools/README.md` | Duplicating too much wrapper detail | Runner docs agree on Stage A/B/C, Playwright, Stage C materializer, and dry-run checks | `rg` stale phrase checks | No new scripts |
| DOC-M4 | Update benchmark and review docs | `benchmark/README.md`, optional `docs/run-reviews/README.md` | Mixing runtime docs and benchmark docs | Benchmark README lists current datasets and LLM judge runner support | `find benchmark/datasets`; README references match folders | No benchmark data edits |
| DOC-M5 | Validate and commit | All touched docs | Broken links or stale references remain | No stale wording; key commands present; git diff is docs-only | `rg` checks and `git diff --check` | No source code/config changes |

## Coverage Matrix

| Requirement | Milestone |
| --- | --- |
| Review last 100 commits | DOC-M1 |
| Decide whether root `README.md` needs update | DOC-M1, DOC-M2 |
| Decide whether `docs/` needs update | DOC-M1, DOC-M2, DOC-M3, DOC-M4 |
| Decide whether folder READMEs need update | DOC-M1, DOC-M3, DOC-M4 |
| Reflect staged weekday digest runner | DOC-M2, DOC-M3 |
| Reflect Playwright/browser runner vs Browser Use/Chrome debug role | DOC-M2, DOC-M3 |
| Reflect Stage B article prefetch and Stage C materializer | DOC-M2, DOC-M3 |
| Reflect Russian compact Telegram digest and link preview | DOC-M2, DOC-M3 |
| Reflect benchmark additions from last 100 commits | DOC-M4 |
| Avoid implementing runtime behavior changes | DOC-M2 through DOC-M5 |

## Task 1: Add Plan To Active Plan Index

**Files:**
- Modify: `PLANS.md`

- [ ] **Step 1: Add active plan row**

Add this row under `## Active Plan`:

```md
| Documentation Refresh After Runner Work | planned | `docs/superpowers/plans/2026-05-05-documentation-refresh.md` | Update root, operator, tool, onboarding, and benchmark docs after the last 100 commits introduced the staged Codex weekday runner, Playwright/browser prefetch, Stage B article prefetch, deterministic Stage C, Russian Telegram gates, compact template, and benchmark judge additions. |
```

- [ ] **Step 2: Verify the row is present**

Run:

```bash
rg -n "Documentation Refresh After Runner Work|2026-05-05-documentation-refresh" PLANS.md
```

Expected output includes both strings.

- [ ] **Step 3: Commit the index update**

Run:

```bash
git add PLANS.md docs/superpowers/plans/2026-05-05-documentation-refresh.md
git commit -m "Plan documentation refresh"
```

Expected: one docs-only commit.

## Task 2: Update Root README As The Current Entry Point

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add a current operator path section**

After `## Current State`, add:

````md
## Current Operator Path

The production-like weekday path is the staged Codex wrapper:

```bash
ops/codex-cli/run_schedule.sh weekday_digest
```

For `weekday_digest`, the wrapper runs:

1. source discovery prefetch through `tools/source_discovery_prefetch.py`;
2. Stage A `monitor_sources` inside `codex exec`;
3. Stage B article prefetch through `tools/shortlist_article_prefetch.py`;
4. Stage C finish draft inside `codex exec`;
5. deterministic materialization through `tools/stage_c_finish.py`;
6. Telegram delivery or dry-run through `tools/telegram_send.py`.

The generated digest lives at `digests/YYYY-MM-DD-daily-digest.md`.
Current-run manifests are required under `.state/runs/YYYY-MM-DD/`; a date-level
digest file alone is not enough to mark a scheduled run complete.
````

- [ ] **Step 2: Add setup/test pointers**

Add a short "Runbook quick links" block:

```md
## Runbook Quick Links

| Need | Start here |
| --- | --- |
| New machine or new Cowork session | [`docs/cowork-onboarding.md`](./docs/cowork-onboarding.md) |
| Scheduled Codex runner | [`ops/codex-cli/README.md`](./ops/codex-cli/README.md) |
| Server/systemd/cron launch | [`docs/codex-cli-server-launch.md`](./docs/codex-cli-server-launch.md) |
| Tool contracts and local helper tests | [`tools/README.md`](./tools/README.md) |
| Production-like run reviews | [`docs/run-reviews/`](./docs/run-reviews/) |
| LLM benchmark suite | [`benchmark/README.md`](./benchmark/README.md) |
```

- [ ] **Step 3: Mention compact Russian Telegram digest**

In `Runtime Overview`, update step 3 to:

```md
3. `build_daily_digest` produces the compact Russian `telegram_digest`
   markdown and `daily_brief` from compact artifacts only.
```

- [ ] **Step 4: Verify README references current runner**

Run:

```bash
rg -n "Current Operator Path|run_schedule.sh weekday_digest|stage_c_finish|telegram_digest" README.md
```

Expected: all four terms appear.

- [ ] **Step 5: Commit root README update**

Run:

```bash
git add README.md
git commit -m "Update root README for staged Codex runner"
```

## Task 3: Update Cowork Onboarding For Current Setup

**Files:**
- Modify: `docs/cowork-onboarding.md`

- [ ] **Step 1: Replace Chrome MCP prerequisite wording**

Replace this bullet:

```md
- (Опционально) **Claude in Chrome** MCP — нужен только для источников с `fetch_strategy: chrome_scrape`. Без него blocked-источники просто эмитят `change_request` при попытке fetch.
```

with:

```md
- **Playwright Chromium** for scheduled `fetch_strategy: chrome_scrape` sources. Browser Use / Chrome-style inspection is useful for manual debugging, but scheduled runs use the Playwright-backed `tools/browser_fetch.py` helper.
```

- [ ] **Step 2: Add Playwright install command**

In setup commands after `pip install -r tools/requirements.txt`, add:

```bash
python3 -m playwright install chromium
```

- [ ] **Step 3: Quote `.env` sample values**

Change the sample fetch value to:

```bash
HTTP_USER_AGENT='PropTechMonitor/1.0 (+contact@example.com)'
```

If Telegram thread is empty, show:

```bash
TELEGRAM_MESSAGE_THREAD_ID=''
```

- [ ] **Step 4: Add scheduled wrapper smoke check**

Under smoke tests, add:

```bash
CODEX_RUN_SCHEDULE_SELF_TEST=1 ops/codex-cli/run_schedule.sh weekday_digest
```

Expected result: wrapper self-test prints paths for source prefetch, Stage A prompt, Stage B helper, Stage C prompt, and Stage C materializer.

- [ ] **Step 5: Update repo tour tool list**

In the `tools/` tree, include:

```md
│   ├── source_discovery_prefetch.py    ← runner source prefetch before Codex
│   ├── browser_fetch.py                ← Playwright browser helper
│   ├── shortlist_article_prefetch.py   ← Stage B article prefetch
│   ├── stage_c_finish.py               ← deterministic Stage C materializer
```

- [ ] **Step 6: Verify stale wording is gone**

Run:

```bash
rg -n "Claude in Chrome|chrome_scrape.*change_request|playwright install chromium|run_schedule.sh weekday_digest" docs/cowork-onboarding.md
```

Expected: no stale Chrome MCP prerequisite remains; Playwright and wrapper references are present.

- [ ] **Step 7: Commit onboarding update**

Run:

```bash
git add docs/cowork-onboarding.md
git commit -m "Refresh onboarding for staged runner setup"
```

## Task 4: Update Codex Runner Runbooks

**Files:**
- Modify: `ops/codex-cli/README.md`
- Modify: `docs/codex-cli-server-launch.md`

- [ ] **Step 1: Expand `ops/codex-cli/README.md` file table**

Change the file table to include:

```md
| `prompts/weekday_digest_discovery.md` | Stage A prompt for `monitor_sources` shortlist generation. |
| `prompts/weekday_digest_finish.md` | Stage C prompt for strict finish draft generation. |
```

- [ ] **Step 2: Add verification checklist to `ops/codex-cli/README.md`**

Add under `Victory Digest Production-Like Run`:

```md
Post-run checks:

```bash
python3 tools/validate_runtime_artifacts.py --check all
python3 tools/test_stage_c_finish.py
python3 tools/test_telegram_send.py
python3 tools/telegram_send.py --profile telegram_digest --date YYYY-MM-DD --dry-run < digests/YYYY-MM-DD-daily-digest.md
```

A production-like weekday run should have current-run `scrape_and_enrich` and
`build_daily_digest` manifests, `critical_findings_count = 0`, Russian digest
text, no runtime path leakage, and Telegram dry-run `parts_sent = 1`.
```

- [ ] **Step 3: Replace server launch architecture diagram**

In `docs/codex-cli-server-launch.md`, replace the simple diagram with:

```text
systemd timer or cron
  -> ops/codex-cli/run_schedule.sh weekday_digest
      -> source_discovery_prefetch.py
      -> codex exec Stage A: monitor_sources
      -> shortlist_article_prefetch.py
      -> codex exec Stage C: finish draft
      -> stage_c_finish.py
      -> validate-finish-artifacts
      -> telegram_send.py when delivery env is configured
```

- [ ] **Step 4: Add Playwright install to server setup**

After `pip install -r tools/requirements.txt`, add:

```bash
python3 -m playwright install chromium
```

- [ ] **Step 5: Add self-test and dry-run commands**

Ensure `docs/codex-cli-server-launch.md` includes:

```bash
CODEX_RUN_SCHEDULE_SELF_TEST=1 ops/codex-cli/run_schedule.sh weekday_digest
python3 tools/telegram_send.py --profile telegram_digest --date YYYY-MM-DD --dry-run < digests/YYYY-MM-DD-daily-digest.md
```

- [ ] **Step 6: Verify runner docs agree**

Run:

```bash
rg -n "weekday_digest_discovery|weekday_digest_finish|shortlist_article_prefetch|stage_c_finish|playwright install chromium|parts_sent = 1|parts_sent" ops/codex-cli/README.md docs/codex-cli-server-launch.md
```

Expected: both docs include staged runner and Playwright references.

- [ ] **Step 7: Commit runner docs update**

Run:

```bash
git add ops/codex-cli/README.md docs/codex-cli-server-launch.md
git commit -m "Update Codex runner documentation"
```

## Task 5: Update Tools README

**Files:**
- Modify: `tools/README.md`

- [ ] **Step 1: Fix stale browser runner sentence**

Replace:

```md
Configured `chrome_scrape` sources are reported as `not_attempted` until a non-interactive browser runner exists.
```

with:

```md
Configured `chrome_scrape` sources are attempted through `tools/browser_fetch.py`
when Playwright and the Chromium payload are installed. If the browser runtime is
unavailable, the result is classified as `browser_runtime_unavailable` and the
scheduled run continues with partial source evidence.
```

- [ ] **Step 2: Add Stage B and Stage C sections**

Add concise sections:

```md
## `shortlist_article_prefetch.py`

`shortlist_article_prefetch.py` is the deterministic Stage B helper for
`weekday_digest`. It receives the current-run shortlist shard, fetches article
text only for shortlisted URLs, writes `*-article-prefetch-result.json` and
`*-article-prefetch-summary.json`, and records `body_status_hint` plus
`lead_image` metadata. It does not broaden full-text usage beyond
`scrape_and_enrich`.

Offline contract coverage lives in `tools/test_shortlist_article_prefetch.py`.

## `stage_c_finish.py`

`stage_c_finish.py` validates the strict Stage C finish draft and materializes
current-run `.state/enriched`, `.state/runs`, `.state/briefs`, and
`digests/YYYY-MM-DD-daily-digest.md`. For `telegram_digest`, it enforces Russian
text, compact template markers, raw markdown length, `lead_image`, and
`telegram_preview`.

Offline contract coverage lives in `tools/test_stage_c_finish.py`.
```

- [ ] **Step 3: Mention Telegram preview support**

In `telegram_send.py` section, add:

```md
For `telegram_digest`, the sender keeps the digest as one text message when
possible and uses Telegram `link_preview_options` from the first markdown source
link to request a large preview above the text.
```

- [ ] **Step 4: Verify tool docs**

Run:

```bash
rg -n "browser_runtime_unavailable|shortlist_article_prefetch.py|stage_c_finish.py|lead_image|link_preview_options" tools/README.md
```

Expected: all terms appear.

- [ ] **Step 5: Commit tools README update**

Run:

```bash
git add tools/README.md
git commit -m "Refresh tool documentation for staged weekday pipeline"
```

## Task 6: Update Benchmark README

**Files:**
- Modify: `benchmark/README.md`

- [ ] **Step 1: Add current datasets to structure**

Update the dataset tree to include:

```md
├── request-synthesis/                 ← Request-level thesis synthesis with LLM judge
│   ├── inputs.jsonl
│   ├── golden.jsonl
│   ├── judge_prompt_spec.json
│   ├── judge_schema.json
│   └── judge_calibration.json
└── request-article-synthesis/         ← Article-grounded synthesis with QA review notes
    ├── inputs.jsonl
    ├── golden.jsonl
    ├── judge_prompt_spec.json
    ├── judge_schema.json
    ├── judge_calibration.json
    └── agent_qa_review_notes.json
```

- [ ] **Step 2: Add runner command**

Add:

```md
## Runner

```bash
python3 benchmark/scripts/run_request_benchmarks.py --help
```

Use this runner for request-level benchmark flows. LLM judge datasets include
`judge_prompt_spec.json`, `judge_schema.json`, and `judge_calibration.json`;
they remain expert-review pending unless the dataset metadata says otherwise.
```

- [ ] **Step 3: Update metrics table**

Add rows:

```md
| Request Synthesis | LLM-as-Judge + schema validation | Judge score / critical issue count | expert calibrated |
| Request Article Synthesis | LLM-as-Judge + QA notes | Judge score / grounding failures | expert calibrated |
```

- [ ] **Step 4: Verify benchmark README matches folders**

Run:

```bash
find benchmark/datasets -maxdepth 1 -type d -print | sort
rg -n "request-synthesis|request-article-synthesis|run_request_benchmarks|judge_calibration" benchmark/README.md
```

Expected: README mentions both dataset folders and runner.

- [ ] **Step 5: Commit benchmark README update**

Run:

```bash
git add benchmark/README.md
git commit -m "Update benchmark README for judge datasets"
```

## Task 7: Final Documentation Consistency Pass

**Files:**
- Modify only if checks reveal a concrete stale reference:
  - `docs/run-reviews/README.md`
  - `docs/runtime-architecture.md`
  - `docs/mode-catalog.md`
  - `PLANS.md`

- [ ] **Step 1: Search for stale terms**

Run:

```bash
rg -n "Claude in Chrome|non-interactive browser runner exists|not_attempted until|monolithic|config/monitoring.yaml|MarkdownV2.*telegram_digest|2 message parts|parts_sent: 2|cr_telegram_formatting" README.md docs tools benchmark ops cowork config
```

Expected: any remaining matches are either historical/legacy context explicitly labeled as such or should be fixed in this task.

- [ ] **Step 2: Search for current operator terms**

Run:

```bash
rg -n "run_schedule.sh weekday_digest|source_discovery_prefetch|shortlist_article_prefetch|stage_c_finish|Playwright|telegram_preview|link_preview_options|Russian|русск" README.md docs tools ops
```

Expected: key current concepts are visible from root/operator/tool docs.

- [ ] **Step 3: Run markdown whitespace check**

Run:

```bash
git diff --check
```

Expected: no trailing whitespace or conflict markers.

- [ ] **Step 4: Run runtime artifact validator**

Run:

```bash
python3 tools/validate_runtime_artifacts.py --check all
```

Expected: `PASS  all`. This confirms documentation edits did not accidentally break YAML fixtures or runtime contract references.

- [ ] **Step 5: Mark plan complete in `PLANS.md`**

Change the active plan row status from `planned` to `completed`:

```md
| Documentation Refresh After Runner Work | completed | `docs/superpowers/plans/2026-05-05-documentation-refresh.md` | Updated root, operator, tool, onboarding, and benchmark docs after the last 100 commits introduced the staged Codex weekday runner, Playwright/browser prefetch, Stage B article prefetch, deterministic Stage C, Russian Telegram gates, compact template, and benchmark judge additions. |
```

- [ ] **Step 6: Commit final consistency pass**

Run:

```bash
git add README.md docs tools benchmark ops PLANS.md
git commit -m "Complete documentation refresh"
```

## Self-Review

- Spec coverage: The plan maps the last 100 commits into documentation areas and includes root README, `docs/`, and folder READMEs.
- Placeholder scan: no placeholder markers are present.
- Scope control: The plan is docs-only and explicitly excludes runtime code/config behavior changes.
- Known risk: Some historical plan docs under `docs/plans/` and `docs/superpowers/plans/` intentionally remain as implementation history. The refresh should not rewrite them unless they are linked from root docs as current operational guidance.
