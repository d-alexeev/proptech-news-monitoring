# COMPLETION_AUDIT.md

## Audit Scope

Этот аудит сравнивает текущую ветку с исходным implementation plan из [`PLANS.md`](./PLANS.md).

Источник истины для аудита:

- текущая рабочая копия ветки `main`;
- текущий `HEAD` commit `746cc2e`;
- незакоммиченные изменения в [`PLANS.md`](./PLANS.md), которые влияют на статус milestones;
- фактические файлы репозитория, включая [`AGENTS.md`](./AGENTS.md), [`PLANS.md`](./PLANS.md), [`README.md`](./README.md), [`config/monitoring.yaml`](./config/monitoring.yaml), [`docs/runbook.md`](./docs/runbook.md), [`docs/agent-spec.md`](./docs/agent-spec.md).

Ключевой вывод: реализованы только базовая git-инфраструктура и planning scaffolding. Рефакторинг runtime-архитектуры под `Claude Cowork` по существу ещё не начат.

## Overall Status

- Fully implemented requirements: `1 / 16`
- Partially implemented requirements: `8 / 16`
- Not implemented requirements: `7 / 16`

## Requirement-by-Requirement Audit

| Requirement | Status | Evidence | Notes |
| --- | --- | --- | --- |
| R1 | Not implemented | В репозитории нет `cowork/shared/*`, `cowork/modes/*` или mode-specific runtime contracts. | Runtime still revolves around large docs, config comments, and generic prompts. |
| R2 | Not implemented | Нет job definitions, mode files, trigger map or entry instructions for `Claude Cowork`. | Only the plan for jobs exists. |
| R3 | Not implemented | Нет compact shared briefs. | Knowledge is still spread across `README`, `docs/*`, `config/monitoring.yaml`, `prompts/*`. |
| R4 | Not implemented | Нет режима `scrape_and_enrich`; нет enforcement boundary around full-text usage. | Article storage exists conceptually in config and `.state/articles`, but not in the required architectural form. |
| R5 | Not implemented | `.state` remains monolithic: `dedupe.json`, `delivery-log.json`, `raw/*.json`. | No shard layout implemented. |
| R6 | Partially implemented | `config/monitoring.yaml` and docs define `raw`/`enriched` item shape; `delivery-log.json` has run-like structure. | Required new contracts (`story_brief`, `daily_brief`, `weekly_brief`, `run_manifest`) are not implemented. |
| R7 | Partially implemented | Source-specific knowledge exists in [`config/monitoring.yaml`](./config/monitoring.yaml) comments and [`docs/rss-api-audit.md`](./docs/rss-api-audit.md). | It is not extracted into compact adapter files. |
| R8 | Partially implemented | Source groups, ingestion config, and raw collection artifacts exist. | No dedicated `monitor_sources` mode with explicit contract and outputs. |
| R9 | Not implemented | Daily digests exist as files, but no compact-artifact daily pipeline is implemented. | No `story_brief` / recent `daily_brief`-based architecture. |
| R10 | Not implemented | Weekly digests exist as files, but no weekly pipeline based on `daily_brief` / `weekly_brief` exists. | No brief-based weekly contract. |
| R11 | Partially implemented | There is a manual review artifact: [`docs/daily-digest-mechanism-review.md`](./docs/daily-digest-mechanism-review.md). | No dedicated `review_digest` mode. |
| R12 | Partially implemented | `config/monitoring.yaml` already defines `schedule.breaking_alert` and includes `weekly_context`. | No separate `Claude Cowork` alert mode or compact runtime contract. |
| R13 | Partially implemented | [`config/stakeholders.yaml`](./config/stakeholders.yaml) and [`prompts/digest_personalizer.md`](./prompts/digest_personalizer.md) exist. | Personalization remains disabled and is not implemented as downstream `stakeholder_fanout`. |
| R14 | Partially implemented | [`docs/runbook.md`](./docs/runbook.md) contains some migration notes for `.state`; `PLANS.md` defines M7. | No actual refactor migration/backfill/rollback assets or process implemented. |
| R15 | Partially implemented | `benchmark/` datasets already exist. | No regression harness, no explicit gates, no cutover criteria. |
| R16 | Fully implemented | Git repo initialized; `.gitignore` exists; initial commit exists; `PLANS.md` includes `Git Usage Rules`. | Branch is usable for milestone-scoped development. |

## Fully Implemented Requirements

### R16. Git usage and hygiene

Implemented evidence:

- repository is a git repo;
- current branch exists (`main`);
- baseline commit exists (`746cc2e`);
- [`.gitignore`](./.gitignore) excludes `.env`, `.state/`, `.DS_Store`, editor noise;
- [`PLANS.md`](./PLANS.md) includes git usage rules and `M0`.

## Partially Implemented Requirements

### R6. Handoff contracts

What exists:

- partial schema language in [`config/monitoring.yaml`](./config/monitoring.yaml);
- partial run/log structure in `.state/delivery-log.json`;
- story linkage via `story_id` in `.state/dedupe.json`.

What is missing:

- `story_brief`
- `daily_brief`
- `weekly_brief`
- explicit `run_manifest`
- producer/consumer contract boundaries per mode

### R7. Source adapters

What exists:

- source-specific operational knowledge in docs and config comments.

What is missing:

- compact adapter files;
- source-to-adapter mapping;
- runtime-safe loading rules.

### R8. `monitor_sources`

What exists:

- source groups and ingestion config;
- raw data examples under `.state/raw`.

What is missing:

- dedicated mode contract;
- shortlist artifact as required by the plan;
- explicit “no full text” boundary.

### R11. `review_digest`

What exists:

- one manual QA/review document.

What is missing:

- dedicated mode;
- structured review output contract;
- repeatable QA step in the runtime architecture.

### R12. `breaking_alert`

What exists:

- config-level alert schedule and threshold;
- inclusion of `weekly_context` in alert scope.

What is missing:

- standalone mode contract;
- compact alert input/output artifacts;
- isolation from daily/weekly digest generation.

### R13. `stakeholder_fanout`

What exists:

- stakeholder config;
- personalization prompt;
- documented intent.

What is missing:

- downstream one-profile-per-run mode;
- brief-based input contract;
- execution path separated from base daily/weekly critical path.

### R14. Migration / backfill / rollback

What exists:

- some state migration notes in the runbook;
- milestone planning for a future migration path.

What is missing:

- implemented migration assets;
- runnable backfill process;
- explicit rollback mechanics for the refactor.

### R15. Regression gates

What exists:

- benchmark datasets and benchmark README.

What is missing:

- regression harness;
- smoke subset definition bound to rollout;
- cutover go/no-go gates.

## Not Implemented Requirements

### R1. Minimal runtime inputs per mode

Not implemented because mode boundaries and mode-specific runtime footprints do not exist.

### R2. Separate `Claude Cowork` jobs

Not implemented because there are no runtime jobs, entry instructions, or scheduler-facing mode artifacts in the repo.

### R3. Compact shared runtime briefs

Not implemented because no `cowork/shared/*` structure exists.

### R4. Full text isolated to `scrape_and_enrich`

Not implemented because the required mode does not exist and no enforcement boundary exists.

### R5. Sharded runtime state

Not implemented because `.state` still uses monolithic stores and ad hoc raw files.

### R9. Daily digest on compact artifacts

Not implemented because there is no new daily pipeline architecture based on `enriched_item + story_brief + daily_brief`.

### R10. Weekly digest on daily/weekly briefs

Not implemented because there is no weekly aggregation or trend synthesis pipeline based on briefs.

## Misleading Documentation and Status Claims

### 1. `PLANS.md` shows `M1 = completed`, but that status is not committed

Current working tree marks `M1` as completed, but the branch `HEAD` does not include those changes yet.

Why this is misleading:

- someone reading git history only will see only the initial scaffold commit;
- the branch is currently dirty (`PLANS.md` modified), so milestone status is ahead of committed history.

Recommended correction:

- either commit the `M1` updates;
- or avoid treating `M1` as branch-level completed until committed.

### 2. `PLANS.md` program-level acceptance criteria can be misread as current state

The section is written as unconditional statements, but most of them describe target-state architecture, not what is currently true.

Why this is misleading:

- a quick reader may assume the branch already enforces compact runtime inputs, full-text isolation, and migration safety;
- only the git-related portion is actually true today.

Recommended correction:

- treat these as target acceptance criteria;
- optionally label the section explicitly as target-state criteria.

### 3. `README.md` suggests a runnable `runner`, but no runner implementation exists in the repo

Evidence:

- [`README.md`](./README.md) shows commands like `runner --config ...`;
- no runner binary, script, or wrapper is present in the repository.

Why this is misleading:

- it reads like an executable local project, while the repo is mostly instructions, config, prompts, and artifacts.

Recommended correction:

- either add the actual runner integration artifacts;
- or rewrite the README to say these are expected runner interfaces, not a bundled executable.

### 4. `docs/runbook.md` and `docs/rss-api-audit.md` reference `save_article.py`, but the file does not exist

Evidence:

- both docs instruct the user to run `python3 save_article.py ...`;
- `save_article.py` is missing from the repo.

Why this is misleading:

- the docs imply there is a supporting script for article persistence, but the repository does not provide it.

Recommended correction:

- either add the script;
- or replace the references with the actual intended Cowork/manual workflow.

### 5. `docs/agent-spec.md` claims the pipeline runs in production mode

Evidence:

- the document says: `Пайплайн запущен и работает в production-режиме`.

Why this is misleading in the current branch context:

- this branch does not contain executable runner/job artifacts for the `Claude Cowork` refactor;
- it contains docs, configs, prompts, digests, benchmarks, and local state, but not a packaged runnable implementation of the refactored architecture.

Recommended correction:

- distinguish clearly between legacy/manual operation, documented intent, and implemented refactor status on this branch.

## Exact Next Tasks Needed for Full Completion

### Immediate housekeeping before continuing implementation

1. Commit the current `M1` updates in [`PLANS.md`](./PLANS.md), or explicitly revert the `M1 = completed` claim if it should not be kept.
2. Decide whether audit and plan status should reflect:
   - branch `HEAD`
   - or working tree state
3. Clarify in docs that current branch state is a planning + bootstrap baseline, not the completed refactor.

### Implementation tasks required to finish the plan

4. Implement `M2`: create the `Claude Cowork` job matrix with explicit triggers, inputs, outputs, and downstream handoffs.
5. Implement `M3`: create compact shared runtime briefs and split runtime instructions from large docs.
6. Implement `M4`: extract source-specific knowledge into adapter files and define source-to-adapter mapping.
7. Implement `M5`: split runtime config and define a single runtime source of truth.
8. Implement `M6`: define and introduce sharded state schemas and paths.
9. Implement `M7`: define migration, backfill, and rollback assets for the new state model.
10. Implement `M8`: create the `monitor_sources` mode and its raw/shortlist outputs.
11. Implement `M9`: enforce full-text gating only after shortlist and wire adapter resolution.
12. Implement `M10`: create `scrape_and_enrich` outputs, including `evidence_points`, `body_status`, and `article_file`.
13. Implement `M11`: build daily selection, anti-repeat, and contextualization on compact artifacts.
14. Implement `M12`: emit daily markdown digest plus structured `daily_brief`.
15. Implement `M13`: create the standalone `review_digest` QA mode.
16. Implement `M14`: create weekly aggregation from `daily_brief`.
17. Implement `M15`: implement weekly trend synthesis and `weekly_brief`.
18. Implement `M16`: create standalone `breaking_alert`.
19. Implement `M17`: create downstream `stakeholder_fanout`.
20. Implement `M18`: add legacy exports / compatibility bridge from new shards to old files.
21. Implement `M19`: add regression harness, smoke subsets, parity checks, and cutover gates.

### Documentation correction tasks required for honest completion

22. Update [`README.md`](./README.md) to distinguish between expected runner interface and actual repo-provided implementation.
23. Update [`docs/runbook.md`](./docs/runbook.md) and [`docs/rss-api-audit.md`](./docs/rss-api-audit.md) to remove or replace missing `save_article.py` references unless the script is added.
24. Update [`docs/agent-spec.md`](./docs/agent-spec.md) to separate:
   - legacy/manual capability,
   - planned `Claude Cowork` refactor,
   - actually implemented branch state.

## Final Assessment

Current branch is a valid starting baseline, not a completed implementation of the refactor.

What is genuinely done:

- git bootstrap;
- git hygiene;
- planning discipline scaffolding;
- execution plan authoring.

What is not yet done:

- the actual architectural split into `Claude Cowork` modes;
- compact runtime contracts;
- sharded state;
- migration path;
- daily/weekly/reflection/refanout runtime implementation;
- regression and cutover machinery.
