# Runtime Architecture

## Current Canonical Runtime Layer

Текущая runtime-архитектура этого проекта описывается не legacy `prompts/` и не
монолитным `config/monitoring.yaml`, а следующими canonical слоями:

- [`config/runtime/runtime_manifest.yaml`](../config/runtime/runtime_manifest.yaml)
  — корневой манифест canonical runtime-слоя;
- [`cowork/`](../cowork) — instructions для `Claude Cowork`, включая shared briefs,
  mode prompts и source adapters;
- [`config/runtime/`](../config/runtime) — contracts, config slices, state layout,
  migration, compatibility и regression artifacts.

Этот репозиторий остаётся git-managed source-of-truth для runtime-изменений, даже
если сам агент исполняется во внешнем runner environment.

## Layer Model

### 1. Shared Business and Contract Layer

Файлы в [`cowork/shared/`](../cowork/shared) определяют короткие общие runtime
briefs:

- `mission_brief.md`
- `taxonomy_and_scoring.md`
- `contracts.md`
- `change_request_policy.md`

Эти файлы задают business lens, scoring/taxonomy, artifact contracts и policy
для external runner escalation.

### 2. Mode Layer

Файлы в [`cowork/modes/`](../cowork/modes) описывают отдельные режимы работы
агента:

- `monitor_sources`
- `scrape_and_enrich`
- `build_daily_digest`
- `review_digest`
- `build_weekly_digest`
- `breaking_alert`
- `stakeholder_fanout`

Каждый mode prompt работает только со своим компактным набором входов и не
должен подгружать длинные human docs.

### 3. Adapter Layer

Файлы в [`cowork/adapters/`](../cowork/adapters) хранят source-specific runtime
knowledge для нестандартных источников.

Адаптеры подгружаются только по `source_id`, когда это реально требуется для
текущего прогона, а не целиком.

### 4. Runtime Config Layer

Файлы в [`config/runtime/`](../config/runtime) являются canonical runtime
configuration:

- `source-groups/` — разбиение источников по группам;
- `runtime_thresholds.yaml` — thresholds, scoring inputs и tracked entities;
- `schedule_bindings.yaml` — schedules и delivery profile bindings;
- `mode-contracts/` — explicit contracts по режимам;
- `state_layout.yaml` и `state_schemas.yaml` — canonical state model;
- `regression_harness.yaml` — regression and rollout gates;
- `legacy_exports.yaml` — export-only compatibility bridge.

### 5. State Layer

Canonical state layout задаётся в
[`config/runtime/state_layout.yaml`](../config/runtime/state_layout.yaml).
Рабочие артефакты шардируются по типу, дате и run context:

- `raw`
- `shortlists`
- `enriched`
- `stories`
- `briefs/daily`
- `briefs/weekly`
- `reviews`
- `change-requests`
- `articles`

Legacy `dedupe.json` и `delivery-log.json` больше не являются critical-path
источниками памяти; они рассматриваются как compatibility/export layer.

## Core Runtime Flow

Базовый поток теперь выглядит так:

1. `monitor_sources` discovers candidates и выпускает `raw_candidate` +
   `shortlisted_item`.
2. `scrape_and_enrich` работает только по shortlist и является единственным
   mode, где full article text — primary working input.
3. `build_daily_digest` собирает markdown digest + `daily_brief` только из
   compact artifacts.
4. `review_digest` выполняет QA-review без переписывания digest.
5. `build_weekly_digest` работает по `daily_brief` и bounded `weekly_brief`
   history.
6. `breaking_alert` остаётся отдельным alert-only path.
7. `stakeholder_fanout` делает downstream personalization вне base critical path.

## Full Text Rule

Full article text не является дефолтным runtime input.

- Разрешён как primary working input только в `scrape_and_enrich`.
- Daily, weekly, review и fanout режимы работают по compact artifacts и briefs.
- Если внешний агент упирается в blocked/manual source, scrape failure или
  adapter gap, он должен выпустить `change_request`, а не менять runtime files.

## Change Request Loop

Follow-up escalation loop задаётся следующими canonical файлами:

- [`cowork/shared/change_request_policy.md`](../cowork/shared/change_request_policy.md)
- [`config/runtime/change_request_schema.yaml`](../config/runtime/change_request_schema.yaml)
- [`config/runtime/change_request_intake_workflow.md`](../config/runtime/change_request_intake_workflow.md)

Это гарантирует, что persistent fixes планируются и коммитятся здесь, в
source-of-truth репозитории, а не во внешнем runner instance.
