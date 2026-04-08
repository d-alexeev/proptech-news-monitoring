# PropTech News Monitoring

Git-managed source-of-truth репозиторий для proptech monitoring agent под
управлением `Claude Cowork`.

Текущий проект описывает canonical runtime layer агента: prompts/instructions,
runtime contracts, source adapters, config slices, state layout, change-request
policy и regression gates. Сам runner может исполняться вне этого репозитория.

## Цель

Агент должен не просто собирать новости, а отвечать на вопрос:

> "Что из происходящего на глобальном рынке proptech может повлиять на стратегию, продукт, монетизацию, спрос, supply или конкурентный ландшафт Авито Недвижимости?"

---

## Current State

Основной current-state путь больше не монолитный `runner --config
config/monitoring.yaml`.

Canonical runtime layer теперь находится в:

- [`config/runtime/runtime_manifest.yaml`](./config/runtime/runtime_manifest.yaml)
- [`cowork/`](./cowork)
- [`docs/runtime-architecture.md`](./docs/runtime-architecture.md)
- [`docs/mode-catalog.md`](./docs/mode-catalog.md)

Legacy файлы вроде [`config/monitoring.yaml`](./config/monitoring.yaml),
[`config/stakeholders.yaml`](./config/stakeholders.yaml), части старых docs и
старые `prompts/` сохраняются как reference/compatibility layer и не должны
считаться главным описанием текущего runtime-дизайна.

## Canonical Runtime Structure

```
PropTech News Monitoring/
├── config/runtime/                   ← canonical runtime config, contracts and fixtures
├── cowork/shared/                    ← shared briefs and change-request policy
├── cowork/modes/                     ← mode prompts for Claude Cowork
├── cowork/adapters/                  ← source-specific runtime notes
├── docs/runtime-architecture.md      ← canonical runtime architecture doc
├── docs/mode-catalog.md              ← canonical mode catalog
├── digests/                          ← generated digest artifacts
└── .state/                           ← sharded runtime state (gitignored)
```

---

## Runtime Overview

Текущая architecture model:

1. `monitor_sources` discovers candidates и выпускает `raw_candidate` +
   `shortlisted_item`.
2. `scrape_and_enrich` обрабатывает только shortlist и является единственным
   mode, где full article text допустим как primary working input.
3. `build_daily_digest` собирает markdown digest и `daily_brief` только из
   compact artifacts.
4. `review_digest` выполняет QA-review готового digest.
5. `build_weekly_digest` строится по `daily_brief` и bounded `weekly_brief`
   history.
6. `breaking_alert` остаётся отдельным alert-only mode.
7. `stakeholder_fanout` делает downstream personalization вне base critical path.

Подробности:

- runtime architecture: [docs/runtime-architecture.md](./docs/runtime-architecture.md)
- mode catalog: [docs/mode-catalog.md](./docs/mode-catalog.md)
- runtime manifest: [config/runtime/runtime_manifest.yaml](./config/runtime/runtime_manifest.yaml)

---

## Full Text and Change Requests

В новой architecture:

- full article text используется как primary input только в
  `scrape_and_enrich`;
- downstream daily/weekly/review/fanout режимы работают по compact artifacts;
- внешний агент не должен самостоятельно менять prompts/config/adapters/contracts;
- если для fix нужен persistent change, внешний runner выпускает
  `change_request`, а изменения вносятся уже через Codex и git в этом repo.

Policy и workflow:

- [cowork/shared/change_request_policy.md](./cowork/shared/change_request_policy.md)
- [config/runtime/change_request_schema.yaml](./config/runtime/change_request_schema.yaml)
- [config/runtime/change_request_intake_workflow.md](./config/runtime/change_request_intake_workflow.md)

## Ключевые документы

| Документ | Назначение |
|---|---|
| [config/runtime/runtime_manifest.yaml](./config/runtime/runtime_manifest.yaml) | Canonical runtime entrypoint: contracts, fixtures, config slices and references |
| [docs/runtime-architecture.md](./docs/runtime-architecture.md) | Canonical описание текущей runtime-архитектуры |
| [docs/mode-catalog.md](./docs/mode-catalog.md) | Canonical каталог режимов `Claude Cowork` |
| [docs/launch-rerun-dry-run.md](./docs/launch-rerun-dry-run.md) | Canonical reference по schedules, manual reruns и regression/parity dry-runs |
| [cowork/](./cowork) | Canonical runtime instructions: shared briefs, modes and adapters |
| [docs/agent-spec.md](./docs/agent-spec.md) | Legacy detailed spec; useful as reference, but not current canonical runtime layer |
| [docs/runbook.md](./docs/runbook.md) | Legacy operator/runbook reference; launch/rerun alignment продолжается отдельно |
| [docs/llm-jtbd-analysis.md](./docs/llm-jtbd-analysis.md) | Каталог LLM-задач (JTBD) |
| [docs/rss-api-audit.md](./docs/rss-api-audit.md) | Legacy source audit reference |
| [benchmark/README.md](benchmark/README.md) | LLM benchmark: метрики и инструкция |
| [prompts/](./prompts) | Legacy prompt layer kept for reference and migration history |
