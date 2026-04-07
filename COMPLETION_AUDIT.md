# COMPLETION_AUDIT.md

## Audit Scope

Этот аудит сравнивает текущую ветку с исходным implementation plan из [`PLANS.md`](./PLANS.md).

Источник истины для аудита:

- текущий `HEAD` commit `06568a5`;
- текущий [`PLANS.md`](./PLANS.md) как план требований и milestone-статусов;
- фактические файлы репозитория, включая:
  - [`AGENTS.md`](./AGENTS.md)
  - [`PLANS.md`](./PLANS.md)
  - [`cowork/shared/*`](./cowork/shared)
  - [`cowork/modes/*`](./cowork/modes)
  - [`README.md`](./README.md)
  - [`config/monitoring.yaml`](./config/monitoring.yaml)
  - [`config/stakeholders.yaml`](./config/stakeholders.yaml)
  - [`docs/runbook.md`](./docs/runbook.md)
  - [`docs/agent-spec.md`](./docs/agent-spec.md)
  - existing runtime state under [`.state`](./.state)

Ключевой вывод:

- `M0`, `M1`, `M2`, `M3` реально отражены в ветке;
- репозиторий уже содержит planning scaffolding, git hygiene, committed `Claude Cowork` job matrix и runtime instruction-pack;
- сама runtime-архитектура, contracts, state refactor и orchestration-слой ещё не реализованы.

## Overall Status

- Fully implemented requirements: `2 / 16`
- Partially implemented requirements: `9 / 16`
- Not implemented requirements: `5 / 16`

## Requirement-by-Requirement Audit

| Requirement | Status | Evidence | Notes |
| --- | --- | --- | --- |
| R1 | Partially implemented | [`cowork/modes/*`](./cowork/modes) задают allowed/forbidden inputs; shared runtime pack не тянет длинные docs. | Ограничения описаны на уровне prompt contracts, но ещё не enforced runtime-слоем. |
| R2 | Partially implemented | В [`PLANS.md`](./PLANS.md) есть committed `Claude Cowork Job Matrix`; в [`cowork/modes/*`](./cowork/modes) есть mode prompts. | Нет реальных job definitions, runner wiring или scheduler-facing artifacts. |
| R3 | Fully implemented | Есть [`cowork/shared/mission_brief.md`](./cowork/shared/mission_brief.md), [`cowork/shared/taxonomy_and_scoring.md`](./cowork/shared/taxonomy_and_scoring.md), [`cowork/shared/contracts.md`](./cowork/shared/contracts.md). | Shared runtime knowledge вынесено в компактный instruction-pack. |
| R4 | Partially implemented | [`cowork/modes/scrape_and_enrich.md`](./cowork/modes/scrape_and_enrich.md) делает full text единственным primary input для этого режима; остальные mode prompts explicitly forbid article bodies. | Это пока declarative contract, а не фактически работающий pipeline boundary. |
| R5 | Not implemented | `.state` всё ещё монолитный: `dedupe.json`, `delivery-log.json`, `raw/*.json`. | Sharded state layout не внедрён. |
| R6 | Partially implemented | [`cowork/shared/contracts.md`](./cowork/shared/contracts.md) фиксирует canonical artifact names; `config/monitoring.yaml` уже содержит partial raw/enriched schema language. | Нет детализированных field-level schemas для `story_brief`, `daily_brief`, `weekly_brief`, `run_manifest`. |
| R7 | Not implemented | Нет [`cowork/adapters/*`](./cowork). | Source-specific knowledge всё ещё живёт в comments config и больших docs. |
| R8 | Partially implemented | Есть [`cowork/modes/monitor_sources.md`](./cowork/modes/monitor_sources.md) с purpose, inputs и explicit no-full-text rule. | Нет реального mode execution path и shortlist artifacts в новой архитектуре. |
| R9 | Partially implemented | Есть [`cowork/modes/build_daily_digest.md`](./cowork/modes/build_daily_digest.md), который требует compact inputs only. | Нет фактической daily pipeline реализации на `enriched_item + story_brief + daily_brief`. |
| R10 | Partially implemented | Есть [`cowork/modes/build_weekly_digest.md`](./cowork/modes/build_weekly_digest.md), который требует `daily_brief` / `weekly_brief`. | Нет рабочей weekly aggregation/synthesis реализации. |
| R11 | Partially implemented | Есть [`cowork/modes/review_digest.md`](./cowork/modes/review_digest.md); раньше был только manual review doc. | Нет реального QA mode output contract и execution path. |
| R12 | Partially implemented | `config/monitoring.yaml` already defines `breaking_alert`; есть [`cowork/modes/breaking_alert.md`](./cowork/modes/breaking_alert.md). | Нет рабочего standalone alert mode поверх compact artifacts. |
| R13 | Partially implemented | Есть [`cowork/modes/stakeholder_fanout.md`](./cowork/modes/stakeholder_fanout.md), [`config/stakeholders.yaml`](./config/stakeholders.yaml), [`prompts/digest_personalizer.md`](./prompts/digest_personalizer.md). | Нет downstream execution path и brief-based personalization implementation. |
| R14 | Partially implemented | В [`PLANS.md`](./PLANS.md) есть M7; в [`docs/runbook.md`](./docs/runbook.md) есть some migration notes for existing `.state`. | Нет actual migration/backfill/rollback assets for the refactor. |
| R15 | Partially implemented | `benchmark/` datasets already exist; `PLANS.md` фиксирует regression milestone. | Нет regression harness, smoke subsets, explicit rollout gates. |
| R16 | Fully implemented | Git repo initialized; `.gitignore` exists; baseline commit and follow-up commits exist; `PLANS.md` includes git usage rules. | Branch is ready for milestone-scoped work. |

## Fully Implemented Requirements

### R3. Compact shared runtime briefs

Implemented evidence:

- shared runtime knowledge moved into:
  - [`cowork/shared/mission_brief.md`](./cowork/shared/mission_brief.md)
  - [`cowork/shared/taxonomy_and_scoring.md`](./cowork/shared/taxonomy_and_scoring.md)
  - [`cowork/shared/contracts.md`](./cowork/shared/contracts.md)
- mode prompts in [`cowork/modes/*`](./cowork/modes) are compact and reuse shared briefs instead of repeating long narrative context.

### R16. Git usage and hygiene

Implemented evidence:

- repository is a git repo;
- current branch exists (`main`);
- commit history exists and is milestone-friendly;
- [`.gitignore`](./.gitignore) excludes `.env`, `.state/`, `.DS_Store`, editor noise;
- [`PLANS.md`](./PLANS.md) includes git usage rules and git bootstrap milestone.

## Partially Implemented Requirements

### R1. Minimal runtime inputs per mode

What exists:

- allowed/forbidden inputs are explicitly documented in each file under [`cowork/modes/*`](./cowork/modes);
- the new instruction-pack itself does not reference large docs or benchmark files directly.

What is missing:

- enforcement in actual runtime execution;
- proof that the runner loads only those files;
- artifact-level validation that forbidden inputs are excluded in practice.

### R2. Separate `Claude Cowork` jobs

What exists:

- committed job matrix in [`PLANS.md`](./PLANS.md);
- one prompt file per planned runtime mode under [`cowork/modes/*`](./cowork/modes).

What is missing:

- real job definitions or runner wiring;
- trigger implementation;
- schedule binding to a `Claude Cowork` runner.

### R4. Full text isolated to `scrape_and_enrich`

What exists:

- `scrape_and_enrich` is explicitly designated as the only mode allowed to treat full article text as primary input;
- other mode prompts forbid full article bodies.

What is missing:

- actual pipeline enforcement;
- artifact contracts proving downstream modes can work without article bodies.

### R6. Handoff contracts

What exists:

- canonical artifact names in [`cowork/shared/contracts.md`](./cowork/shared/contracts.md);
- partial schema language in [`config/monitoring.yaml`](./config/monitoring.yaml);
- existing `story_id` linkage in current `.state`.

What is missing:

- field-level schemas;
- producer/consumer specificity;
- concrete `run_manifest`, `story_brief`, `daily_brief`, `weekly_brief` shapes.

### R8. `monitor_sources`

What exists:

- a dedicated runtime mode prompt with no-full-text restriction and expected outputs.

What is missing:

- actual `raw_candidate` / `shortlisted_item` emission path;
- binding to source-group config and checkpoints in real execution.

### R9. Daily digest on compact artifacts

What exists:

- dedicated daily mode prompt that limits inputs to compact artifacts.

What is missing:

- actual compact-artifact pipeline;
- real `daily_brief`;
- selection/context implementation over new artifacts.

### R10. Weekly digest on daily/weekly briefs

What exists:

- dedicated weekly mode prompt built around `daily_brief` and `weekly_brief`.

What is missing:

- actual `daily_brief` / `weekly_brief` artifacts;
- aggregation and trend synthesis implementation.

### R11. `review_digest`

What exists:

- dedicated QA mode prompt;
- legacy manual review material in [`docs/daily-digest-mechanism-review.md`](./docs/daily-digest-mechanism-review.md).

What is missing:

- execution path;
- structured QA output artifact;
- integration after daily/weekly generation.

### R12. `breaking_alert`

What exists:

- config-level alert scheduling and threshold;
- dedicated mode prompt.

What is missing:

- standalone execution path on compact artifacts;
- suppression logic and alert payload generation in implemented form.

### R13. `stakeholder_fanout`

What exists:

- dedicated downstream mode prompt;
- stakeholder config and personalization prompt.

What is missing:

- execution path from `daily_brief` / `weekly_brief`;
- one-profile-per-run implementation;
- delivery or artifact generation in the new architecture.

### R14. Migration / backfill / rollback

What exists:

- plan milestone;
- some migration discussion in legacy runbook.

What is missing:

- actual migration assets;
- backfill procedure tied to new contracts;
- rollback artifact and cutover mechanics.

### R15. Regression gates

What exists:

- benchmark datasets;
- dedicated milestone in plan.

What is missing:

- runnable harness;
- smoke subset definition;
- explicit pass/fail rollout gates.

## Not Implemented Requirements

### R5. Sharded runtime state

Not implemented because `.state` still uses the old monolithic structure and no new shard directories or contracts exist.

### R7. Source adapter pack

Not implemented because there are no adapter files yet; source-specific operational logic still lives in config comments and large docs.

## Misleading Documentation and Status Claims

### 1. `README.md` still suggests a runnable local `runner`, but no runner implementation exists in the repo

Evidence:

- [`README.md`](./README.md) shows commands like `runner --config ...`;
- the repository still contains no runner binary, wrapper, or runnable entrypoint.

Why this is misleading:

- after M2/M3 the repo now clearly looks like a prompt/runtime-architecture project, but the README still reads like an executable packaged service.

Recommended correction:

- either add the actual runner integration artifacts;
- or rewrite the README to say these are expected runner interfaces, not bundled executables.

### 2. `docs/runbook.md` and `docs/rss-api-audit.md` still reference `save_article.py`, but the file does not exist

Evidence:

- both docs instruct the user to run `python3 save_article.py ...`;
- `save_article.py` is absent from the repository.

Why this is misleading:

- the docs imply a real helper script exists for article persistence.

Recommended correction:

- either add the script;
- or replace those steps with the intended `Claude Cowork` / manual flow.

### 3. `docs/agent-spec.md` claims the pipeline runs in production mode

Evidence:

- the document says: `Пайплайн запущен и работает в production-режиме`.

Why this is misleading:

- this branch does not yet contain the implemented `Claude Cowork` refactor;
- it contains plans and runtime prompts, but not the actual new orchestration or state model.

Recommended correction:

- distinguish clearly between legacy/manual operation and implemented refactor state on this branch.

### 4. Old `Cowork` terminology still exists in legacy docs

Evidence:

- several docs still refer to `Cowork` rather than `Claude Cowork`.

Why this is misleading:

- the branch now explicitly names the target runner as `Claude Cowork` in [`AGENTS.md`](./AGENTS.md), [`PLANS.md`](./PLANS.md), and the new instruction-pack;
- the mixed terminology makes it unclear whether the docs refer to the same execution environment.

Recommended correction:

- normalize naming in legacy docs where the intended runner is the same system.

### 5. `PLANS.md` program-level acceptance criteria still read like current-state facts

Why this is misleading:

- many bullets in `Program-Level Acceptance Criteria` describe the target architecture, not the current implemented branch state.
- after M2/M3 this is less misleading than before, but still not fully accurate.

Recommended correction:

- label them explicitly as target-state acceptance criteria for the full refactor.

## Exact Next Tasks Needed for Full Completion

### Immediate next milestone tasks

1. Implement `M4`: create [`cowork/adapters/*`](./cowork) and extract source-specific operational knowledge from:
   - [`docs/rss-api-audit.md`](./docs/rss-api-audit.md)
   - [`docs/runbook.md`](./docs/runbook.md)
   - relevant comments in [`config/monitoring.yaml`](./config/monitoring.yaml)
2. Define source-to-adapter mapping and make it reviewable as a compact runtime asset.

### Core architecture tasks still required

3. Implement `M5`: split runtime config into smaller runtime source-of-truth artifacts.
4. Implement `M6`: define and add detailed field-level schemas plus sharded state layout.
5. Implement `M7`: add migration, backfill, and rollback artifacts for the state refactor.
6. Implement `M8`: create actual `monitor_sources` execution contract and outputs.
7. Implement `M9`: enforce full-text gating only after shortlist and wire adapter resolution.
8. Implement `M10`: create actual `scrape_and_enrich` outputs, including `evidence_points`, `body_status`, `article_file`, and updated story memory.
9. Implement `M11`: implement daily selection, anti-repeat, and contextualization on compact artifacts.
10. Implement `M12`: emit real daily markdown digest plus structured `daily_brief`.
11. Implement `M13`: implement the standalone `review_digest` QA flow.
12. Implement `M14`: implement weekly aggregation from `daily_brief`.
13. Implement `M15`: implement weekly trend synthesis and `weekly_brief`.
14. Implement `M16`: implement standalone `breaking_alert`.
15. Implement `M17`: implement downstream `stakeholder_fanout`.
16. Implement `M18`: add compatibility exports from new shards to old stores.
17. Implement `M19`: add regression harness, smoke subsets, parity checks, and cutover gates.

### Documentation correction tasks still required

18. Update [`README.md`](./README.md) to clarify that `runner --config ...` is an expected interface, not a repo-provided binary, unless such a binary is added.
19. Update [`docs/runbook.md`](./docs/runbook.md) and [`docs/rss-api-audit.md`](./docs/rss-api-audit.md) to remove or replace missing `save_article.py` references unless the script is added.
20. Update legacy docs to normalize `Cowork` vs `Claude Cowork` naming where they refer to the same runner.
21. Update [`docs/agent-spec.md`](./docs/agent-spec.md) to distinguish:
   - legacy/manual operation;
   - planned refactor architecture;
   - actually implemented branch state.

## Final Assessment

Current branch is no longer just a planning baseline.

What is genuinely implemented now:

- git bootstrap and repo hygiene;
- milestone discipline in `PLANS.md`;
- committed `Claude Cowork` job matrix;
- compact shared runtime briefs;
- compact per-mode runtime prompt skeletons.

What is still not implemented:

- source adapter layer;
- split runtime config;
- sharded state;
- migration path;
- real compact-artifact pipeline for daily/weekly/review/alert/personalization;
- regression and rollout machinery.

In short:

- the branch now contains the first real implementation layer of the refactor: runtime instruction architecture;
- it does not yet contain the operational runtime system that those instructions describe.
