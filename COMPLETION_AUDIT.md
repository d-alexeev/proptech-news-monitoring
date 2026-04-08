# COMPLETION_AUDIT.md

## Scope

Этот аудит сравнивает текущую ветку с исходным implementation plan из [`PLANS.md`](./PLANS.md).

Аудит выполнен по состоянию на:

- `HEAD`: `1b4fbee` (`Define weekly trend synthesis contract`)
- репозиторий: contract/config/prompt-oriented, практически без исполняемого кода

Источники истины для аудита:

- [`PLANS.md`](./PLANS.md)
- runtime artifacts under [`config/runtime/`](./config/runtime)
- runtime prompt pack under [`cowork/`](./cowork)
- legacy docs and config:
  - [`README.md`](./README.md)
  - [`config/monitoring.yaml`](./config/monitoring.yaml)
  - [`config/stakeholders.yaml`](./config/stakeholders.yaml)
  - [`docs/runbook.md`](./docs/runbook.md)
  - [`docs/agent-spec.md`](./docs/agent-spec.md)
  - [`docs/rss-api-audit.md`](./docs/rss-api-audit.md)
- existing digests under [`digests/`](./digests)
- git history on the current branch

## Status Model

В этом аудите используется следующая интерпретация статусов:

- `Fully implemented`:
  требование реализовано на уровне repo artifacts, то есть в виде prompts/contracts/config/schemas/fixtures, и для него больше не остаётся незакрытого milestone внутри текущего плана.
- `Partially implemented`:
  в репозитории уже есть существенный artifact layer, но требование ещё не доведено до полной формы по плану или зависит от ещё не реализованных milestones.
- `Not implemented`:
  в репозитории нет достаточного artifact layer, чтобы считать требование реально введённым.

Важно: `Fully implemented` в этом аудите означает завершённость на уровне артефактов и архитектурных контрактов внутри текущего плана. Это не то же самое, что end-to-end cutover старого пайплайна на новый runtime.

## Overall Summary

- Fully implemented requirements: `10 / 16`
- Partially implemented requirements: `5 / 16`
- Not implemented requirements: `1 / 16`

Ключевой вывод:

- `M0-M15` действительно реализованы как planning/config/contract layer.
- Основной архитектурный каркас уже собран: shared briefs, adapters, split runtime config, shard schemas, migration plan, mode contracts для `monitor_sources`, `scrape_and_enrich`, `build_daily_digest`, `review_digest`, `build_weekly_digest`.
- Основные пробелы теперь сосредоточены в `breaking_alert`, `stakeholder_fanout`, compatibility bridge и regression gates.
- Legacy docs всё ещё описывают старый pipeline как будто он остаётся текущим рабочим runtime.

## Requirement-by-Requirement Audit

| Requirement | Status | Evidence | Notes |
| --- | --- | --- | --- |
| `R1` | Partially implemented | [`cowork/modes/`](./cowork/modes), [`PLANS.md`](./PLANS.md), mode contracts under [`config/runtime/mode-contracts/`](./config/runtime/mode-contracts) | Все режимы имеют prompt-level allowed/forbidden inputs, но `breaking_alert` и `stakeholder_fanout` всё ещё без dedicated contracts/fixtures. |
| `R2` | Partially implemented | Job matrix in [`PLANS.md`](./PLANS.md), schedules in [`config/runtime/schedule_bindings.yaml`](./config/runtime/schedule_bindings.yaml), mode prompts in [`cowork/modes/`](./cowork/modes) | Агент логически разложен на jobs, но runner-facing job definitions и contract coverage для всех jobs ещё не завершены. |
| `R3` | Fully implemented | [`cowork/shared/mission_brief.md`](./cowork/shared/mission_brief.md), [`cowork/shared/taxonomy_and_scoring.md`](./cowork/shared/taxonomy_and_scoring.md), [`cowork/shared/contracts.md`](./cowork/shared/contracts.md) | Shared runtime knowledge вынесено в компактные shared briefs. |
| `R4` | Fully implemented | [`config/runtime/mode-contracts/scrape_and_enrich_gate.yaml`](./config/runtime/mode-contracts/scrape_and_enrich_gate.yaml), [`config/runtime/mode-contracts/scrape_and_enrich_output.yaml`](./config/runtime/mode-contracts/scrape_and_enrich_output.yaml), downstream prompts in [`cowork/modes/`](./cowork/modes) | `scrape_and_enrich` объявлен единственным full-text consumer, downstream режимы запрещают `full article bodies` / `./.state/articles/`. |
| `R5` | Partially implemented | [`config/runtime/state_layout.yaml`](./config/runtime/state_layout.yaml), [`config/runtime/state_schemas.yaml`](./config/runtime/state_schemas.yaml), [`config/runtime/migration_plan.md`](./config/runtime/migration_plan.md) | Sharded state спроектирован, но live critical path ещё не переключён и compatibility bridge ещё не реализован. |
| `R6` | Fully implemented | [`config/runtime/state_schemas.yaml`](./config/runtime/state_schemas.yaml), [`config/runtime/state-fixtures/valid_artifacts.yaml`](./config/runtime/state-fixtures/valid_artifacts.yaml), [`config/runtime/state_layout.yaml`](./config/runtime/state_layout.yaml) | Основные handoff contracts заданы и покрыты fixture-level schemas. |
| `R7` | Fully implemented | [`cowork/adapters/source_map.md`](./cowork/adapters/source_map.md), files under [`cowork/adapters/`](./cowork/adapters) | Source-specific knowledge вынесено в компактный adapter layer. |
| `R8` | Fully implemented | [`config/runtime/mode-contracts/monitor_sources.yaml`](./config/runtime/mode-contracts/monitor_sources.yaml), fixtures under [`config/runtime/mode-fixtures/`](./config/runtime/mode-fixtures), [`cowork/modes/monitor_sources.md`](./cowork/modes/monitor_sources.md) | `monitor_sources` формализован как discovery/triage/shortlist mode без full text. |
| `R9` | Fully implemented | [`config/runtime/mode-contracts/build_daily_digest_selection.yaml`](./config/runtime/mode-contracts/build_daily_digest_selection.yaml), [`config/runtime/mode-contracts/build_daily_digest_rendering.yaml`](./config/runtime/mode-contracts/build_daily_digest_rendering.yaml), daily fixtures | Daily path зафиксирован через compact artifacts only: selection, anti-repeat, contextualization, rendering, `daily_brief`. |
| `R10` | Fully implemented | [`config/runtime/mode-contracts/build_weekly_digest_aggregation.yaml`](./config/runtime/mode-contracts/build_weekly_digest_aggregation.yaml), [`config/runtime/mode-contracts/build_weekly_digest_trends.yaml`](./config/runtime/mode-contracts/build_weekly_digest_trends.yaml), weekly fixtures | Weekly path зафиксирован через `daily_brief` + limited `weekly_brief` history, без raw/full-text/archive зависимости. |
| `R11` | Fully implemented | [`config/runtime/mode-contracts/review_digest.yaml`](./config/runtime/mode-contracts/review_digest.yaml), [`config/runtime/state_schemas.yaml`](./config/runtime/state_schemas.yaml), review fixtures | Есть отдельный QA mode с собственным output artifact `qa_review_report`. |
| `R12` | Partially implemented | [`cowork/modes/breaking_alert.md`](./cowork/modes/breaking_alert.md), [`config/runtime/schedule_bindings.yaml`](./config/runtime/schedule_bindings.yaml), job matrix in [`PLANS.md`](./PLANS.md) | Режим и расписание есть, `weekly_context` подключён в schedule, но mode contract и fixtures ещё отсутствуют. |
| `R13` | Partially implemented | [`cowork/modes/stakeholder_fanout.md`](./cowork/modes/stakeholder_fanout.md), profiles under [`config/runtime/stakeholder-profiles/`](./config/runtime/stakeholder-profiles) | Profile layer вынесен, но нет explicit mode contract, fixtures и downstream proof-by-artifact. |
| `R14` | Fully implemented | [`config/runtime/migration_plan.md`](./config/runtime/migration_plan.md), [`config/runtime/migration-fixtures/recent_runs.yaml`](./config/runtime/migration-fixtures/recent_runs.yaml), [`config/runtime/migration-fixtures/rollback_checklist.yaml`](./config/runtime/migration-fixtures/rollback_checklist.yaml) | Migration/backfill/rollback path оформлен как отдельный artifact set. |
| `R15` | Not implemented | [`benchmark/`](./benchmark) exists, but no new regression harness artifacts under `config/runtime/` or rollout gates in plan execution outputs | `M19` полностью pending. JTBD smoke gates и cutover checklist ещё не введены как новые refactor artifacts. |
| `R16` | Fully implemented | [`.gitignore`](./.gitignore), git history up to `1b4fbee`, git usage rules in [`PLANS.md`](./PLANS.md) | Milestone-scoped git workflow и базовая hygiene реально используются. |

## Fully Implemented Requirements

### `R3` — Compact shared runtime briefs

Evidence:

- [`cowork/shared/mission_brief.md`](./cowork/shared/mission_brief.md)
- [`cowork/shared/taxonomy_and_scoring.md`](./cowork/shared/taxonomy_and_scoring.md)
- [`cowork/shared/contracts.md`](./cowork/shared/contracts.md)

Why it counts as fully implemented:

- shared runtime knowledge больше не размазано только по старым docs/prompts;
- canonical shared context вынесен в отдельный runtime-safe набор файлов.

### `R4` — Full text isolated to `scrape_and_enrich`

Evidence:

- [`config/runtime/mode-contracts/scrape_and_enrich_gate.yaml`](./config/runtime/mode-contracts/scrape_and_enrich_gate.yaml)
- [`config/runtime/mode-contracts/scrape_and_enrich_output.yaml`](./config/runtime/mode-contracts/scrape_and_enrich_output.yaml)
- downstream mode prompts under [`cowork/modes/`](./cowork/modes)

Why it counts as fully implemented:

- full-text gate задан явно;
- `scrape_and_enrich` объявлен единственным full-text consumer;
- остальные режимы контрактно запрещают full article bodies и article archive.

### `R6` — Explicit handoff contracts

Evidence:

- [`config/runtime/state_schemas.yaml`](./config/runtime/state_schemas.yaml)
- [`config/runtime/state_layout.yaml`](./config/runtime/state_layout.yaml)
- [`config/runtime/state-fixtures/valid_artifacts.yaml`](./config/runtime/state-fixtures/valid_artifacts.yaml)

Why it counts as fully implemented:

- все основные handoff artifacts из плана имеют schema-level contract;
- producer/consumer ownership and shard rules уже заданы.

### `R7` — Source adapter layer

Evidence:

- [`cowork/adapters/source_map.md`](./cowork/adapters/source_map.md)
- adapter files under [`cowork/adapters/`](./cowork/adapters)

Why it counts as fully implemented:

- нестандартные источники вынесены в отдельные adapters;
- source-specific knowledge больше не живёт только в больших legacy docs.

### `R8` — `monitor_sources` without full text

Evidence:

- [`config/runtime/mode-contracts/monitor_sources.yaml`](./config/runtime/mode-contracts/monitor_sources.yaml)
- [`config/runtime/mode-fixtures/monitor_sources_shortlist.yaml`](./config/runtime/mode-fixtures/monitor_sources_shortlist.yaml)
- [`config/runtime/mode-fixtures/monitor_sources_duplicate_story.yaml`](./config/runtime/mode-fixtures/monitor_sources_duplicate_story.yaml)

Why it counts as fully implemented:

- discovery, triage, shortlist outputs и duplicate-linking уже formalized;
- full text explicitly forbidden in this mode.

### `R9` — Daily digest from compact artifacts only

Evidence:

- [`config/runtime/mode-contracts/build_daily_digest_selection.yaml`](./config/runtime/mode-contracts/build_daily_digest_selection.yaml)
- [`config/runtime/mode-contracts/build_daily_digest_rendering.yaml`](./config/runtime/mode-contracts/build_daily_digest_rendering.yaml)
- daily fixtures under [`config/runtime/mode-fixtures/`](./config/runtime/mode-fixtures)

Why it counts as fully implemented:

- daily path закрыт от selection до `daily_brief`;
- anti-repeat, contextualization и rendering описаны без raw/full-text dependency.

### `R10` — Weekly digest from daily/weekly briefs only

Evidence:

- [`config/runtime/mode-contracts/build_weekly_digest_aggregation.yaml`](./config/runtime/mode-contracts/build_weekly_digest_aggregation.yaml)
- [`config/runtime/mode-contracts/build_weekly_digest_trends.yaml`](./config/runtime/mode-contracts/build_weekly_digest_trends.yaml)
- weekly fixtures under [`config/runtime/mode-fixtures/`](./config/runtime/mode-fixtures)

Why it counts as fully implemented:

- weekly aggregation и trend synthesis ограничены `daily_brief` / bounded `weekly_brief`;
- contract layer explicitly forbids raw/archive/full-text inputs.

### `R11` — Separate `review_digest` QA mode

Evidence:

- [`config/runtime/mode-contracts/review_digest.yaml`](./config/runtime/mode-contracts/review_digest.yaml)
- `qa_review_report` schema in [`config/runtime/state_schemas.yaml`](./config/runtime/state_schemas.yaml)
- review fixtures under [`config/runtime/mode-fixtures/`](./config/runtime/mode-fixtures)

Why it counts as fully implemented:

- QA mode существует как отдельный runtime artifact path;
- output сгруппирован по actionable QA categories, а не подменяет digest.

### `R14` — Migration/backfill/rollback path

Evidence:

- [`config/runtime/migration_plan.md`](./config/runtime/migration_plan.md)
- [`config/runtime/migration-fixtures/recent_runs.yaml`](./config/runtime/migration-fixtures/recent_runs.yaml)
- [`config/runtime/migration-fixtures/rollback_checklist.yaml`](./config/runtime/migration-fixtures/rollback_checklist.yaml)

Why it counts as fully implemented:

- переходный путь задокументирован;
- есть fixture-backed sample cases и rollback checklist.

### `R16` — Git hygiene and milestone-scoped history

Evidence:

- [`.gitignore`](./.gitignore)
- git history from `746cc2e` to `1b4fbee`
- git usage rules in [`PLANS.md`](./PLANS.md)

Why it counts as fully implemented:

- git реально используется как основной review/rollback mechanism для refactor work.

## Partially Implemented Requirements

### `R1` — Minimal explicit runtime inputs for every mode

Что уже есть:

- job matrix в [`PLANS.md`](./PLANS.md);
- prompt-level allowed/forbidden inputs у всех режимов в [`cowork/modes/`](./cowork/modes);
- detailed contracts для `monitor_sources`, `scrape_and_enrich`, `build_daily_digest`, `review_digest`, `build_weekly_digest`.

Что ещё не хватает:

- dedicated contracts/fixtures для `breaking_alert` и `stakeholder_fanout`;
- единообразного contract coverage для всех runtime modes.

### `R2` — Separate `Claude Cowork` jobs with explicit IO and schedules

Что уже есть:

- job matrix in [`PLANS.md`](./PLANS.md);
- schedules in [`config/runtime/schedule_bindings.yaml`](./config/runtime/schedule_bindings.yaml);
- per-mode prompts in [`cowork/modes/`](./cowork/modes).

Что ещё не хватает:

- полного contract coverage для всех jobs;
- runner-facing job definitions или эквивалентного artifact layer для `breaking_alert` и `stakeholder_fanout`.

### `R5` — Sharded state on the critical path

Что уже есть:

- shard layout and schemas in [`config/runtime/state_layout.yaml`](./config/runtime/state_layout.yaml) and [`config/runtime/state_schemas.yaml`](./config/runtime/state_schemas.yaml);
- migration plan exists.

Что ещё не хватает:

- compatibility bridge из новых shards в legacy outputs;
- artifact-level доказательства, что old monoliths больше не нужны live consumers;
- cutover safety layer from `M18`.

### `R12` — Separate `breaking_alert` mode with `weekly_context`

Что уже есть:

- prompt under [`cowork/modes/breaking_alert.md`](./cowork/modes/breaking_alert.md);
- schedule includes `weekly_context` in [`config/runtime/schedule_bindings.yaml`](./config/runtime/schedule_bindings.yaml).

Что ещё не хватает:

- explicit mode contract;
- fixtures for true positive, false positive, duplicate suppression;
- output contract for alert payload.

### `R13` — Downstream `stakeholder_fanout`

Что уже есть:

- prompt under [`cowork/modes/stakeholder_fanout.md`](./cowork/modes/stakeholder_fanout.md);
- split profile configs under [`config/runtime/stakeholder-profiles/`](./config/runtime/stakeholder-profiles).

Что ещё не хватает:

- explicit mode contract;
- profile-based fixtures;
- artifact-level proof that fanout uses only `daily_brief` / `weekly_brief`.

## Not Implemented Requirements

### `R15` — Regression gates and benchmark/smoke checks before cutover

Что уже есть:

- legacy benchmark materials under [`benchmark/`](./benchmark).

Чего нет:

- refactor-specific regression harness;
- smoke subsets for `JTBD-06/07/08/09`;
- cutover checklist as rollout gate artifact;
- parity thresholds and failure policy.

Итог:

- `R15` остаётся полностью незавершённым и напрямую зависит от `M19`.

## Misleading Documentation and Status Claims

### 1. [`README.md`](./README.md) описывает старый runtime как будто он всё ещё основной

Проблемы:

- называет [`config/monitoring.yaml`](./config/monitoring.yaml) “основным конфигом”, хотя canonical runtime source of truth уже перенесён в [`config/runtime/`](./config/runtime);
- показывает запуск через `runner --config ...`, но `runner` в репозитории отсутствует;
- описывает старую структуру `.state` с `dedupe.json` / `delivery-log.json` как центральную runtime-модель;
- по-прежнему завязан на legacy `prompts/*`, а не на `cowork/shared/*` и `cowork/modes/*`.

### 2. [`docs/runbook.md`](./docs/runbook.md) продолжает описывать legacy pipeline как текущий

Проблемы:

- использует `monitor-list.json` + [`config/monitoring.yaml`](./config/monitoring.yaml) как main runtime path;
- описывает contextualization через `delivery-log.json + digests/` и `prompts/contextualizer.md`, что расходится с новой daily/weekly contract architecture;
- многократно ссылается на `save_article.py`, которого в репозитории нет;
- предполагает прямое обновление `dedupe.json`, хотя новое состояние уже спроектировано как shard-based.

### 3. [`docs/agent-spec.md`](./docs/agent-spec.md) смешивает старую и новую архитектуру

Проблемы:

- контекстуализация всё ещё описана через `delivery-log.json + digests/`;
- weekly trends всё ещё привязаны к `prompts/trend_synthesizer.md` и полному архиву выпусков;
- сущности данных и pipeline steps опираются на старый enrichment path и `monitoring.yaml`;
- есть статусные утверждения вроде “alert mode — сконфигурирован” и “memory of previous sends — dedupe.json”, которые больше не соответствуют целевой архитектуре ветки.

### 4. [`docs/rss-api-audit.md`](./docs/rss-api-audit.md) и related docs описывают несуществующий operational tooling

Проблемы:

- содержат инструкции по `save_article.py`, которого нет;
- предполагают, что `dedupe.json` остаётся рабочим местом записи для full-text metadata;
- местами описывают old critical path как актуальный.

### 5. [`config/monitoring.yaml`](./config/monitoring.yaml) корректно помечен как legacy bridge, но всё ещё выглядит как “главный runtime-конфиг”

Проблемы:

- внутри файла остаётся большой объём legacy runtime semantics;
- без чтения [`config/runtime/runtime_manifest.yaml`](./config/runtime/runtime_manifest.yaml) легко ошибочно принять его за canonical source of truth.

### 6. Статус в [`PLANS.md`](./PLANS.md) может быть неверно интерпретирован

Что именно может ввести в заблуждение:

- `M0-M15 = completed` верно для contract/design-layer milestones;
- это не означает, что branch уже содержит end-to-end cutover старого пайплайна на новый runtime;
- без явной оговорки читатель может решить, что operational implementation почти завершена, хотя `M16-M19` и docs-alignment ещё не сделаны.

Итог:

- главный риск сейчас не в отсутствии артефактов, а в том, что legacy docs создают ложную картину “старый pipeline всё ещё canonical”.

## Exact Next Tasks Needed for Full Completion

### 1. Implement `M16` — `breaking_alert`

Нужно добавить:

- [`config/runtime/mode-contracts/breaking_alert.yaml`](./config/runtime/mode-contracts)
- fixtures:
  - true positive high-signal from `weekly_context`
  - false positive high-score but not breaking
  - duplicate follow-up suppression
- manifest linkage in [`config/runtime/runtime_manifest.yaml`](./config/runtime/runtime_manifest.yaml)
- prompt sync in [`cowork/modes/breaking_alert.md`](./cowork/modes/breaking_alert.md)

Критерий завершения:

- `R12` становится fully implemented.

### 2. Implement `M17` — `stakeholder_fanout`

Нужно добавить:

- [`config/runtime/mode-contracts/stakeholder_fanout.yaml`](./config/runtime/mode-contracts)
- fixtures:
  - product vs strategy differentiation
  - one-profile-per-run validation
  - no raw/full-text guard
- manifest linkage
- prompt sync in [`cowork/modes/stakeholder_fanout.md`](./cowork/modes/stakeholder_fanout.md)

Критерий завершения:

- `R13` становится fully implemented;
- `R1` и `R2` продвигаются к полному покрытию всех runtime modes.

### 3. Implement `M18` — Legacy Exports and Compatibility Bridge

Нужно добавить:

- explicit export contracts from shard-era artifacts to legacy `dedupe.json` and `delivery-log.json`
- parity fixtures for one daily and one weekly window
- compatibility notes for old consumers

Критерий завершения:

- `R5` становится fully implemented;
- появляется доказуемый bridge between new shards and old readers.

### 4. Implement `M19` — Regression Harness and Rollout Gates

Нужно добавить:

- smoke subsets for `JTBD-06`, `JTBD-07`, `JTBD-08`, `JTBD-09`
- parity window definition
- failure thresholds
- rollout/cutover checklist

Критерий завершения:

- `R15` становится fully implemented.

### 5. Do a docs-alignment pass immediately after `M16-M19`

Нужно обновить как минимум:

- [`README.md`](./README.md)
- [`docs/runbook.md`](./docs/runbook.md)
- [`docs/agent-spec.md`](./docs/agent-spec.md)
- [`docs/rss-api-audit.md`](./docs/rss-api-audit.md)
- при необходимости comments in [`config/monitoring.yaml`](./config/monitoring.yaml) and [`config/stakeholders.yaml`](./config/stakeholders.yaml)

Что именно исправить:

- убрать ссылки на отсутствующий `runner`;
- убрать ссылки на отсутствующий `save_article.py`;
- явно пометить legacy docs как legacy, если они не переписываются полностью;
- перенести описание canonical runtime на `config/runtime/*` and `cowork/*`.

### 6. Refresh the completion audit after `M16-M19`

Нужно повторно проверить:

- статусы `R1`, `R2`, `R5`, `R12`, `R13`, `R15`;
- соответствие docs новому runtime;
- чистоту branch state и корректность финального milestone coverage.

## Final Audit Verdict

Текущая ветка уже закрывает большую часть архитектурного refactor plan на уровне артефактов:

- shared runtime briefs, adapters, split config, shard schemas, migration path, daily/weekly/review contracts уже есть;
- старый монолитный pipeline больше не является единственной описанной архитектурой;
- `M16-M19` остаются последним обязательным блоком до полного завершения плана.

Но ветка ещё не должна считаться полностью завершённой:

- `breaking_alert` и `stakeholder_fanout` остаются без полного contract/fixture слоя;
- compatibility bridge и regression gates не реализованы;
- legacy docs пока сильно отстают от фактического состояния refactor branch.
