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

Ранее canonical путь был монолитным: `runner --config
config/monitoring.yaml`. Этот файл и сопутствующие legacy-конфиги
(`config/stakeholders.yaml`, `config/monitoring.example.yaml`, `.env.example`)
удалены; конфигурация теперь целиком живёт в `config/runtime/`.

Canonical runtime layer:

- [`config/runtime/runtime_manifest.yaml`](./config/runtime/runtime_manifest.yaml)
- [`cowork/`](./cowork)
- [`docs/runtime-architecture.md`](./docs/runtime-architecture.md)
- [`docs/mode-catalog.md`](./docs/mode-catalog.md)

Папка `prompts/` сохраняется как reference/migration history и не должна
считаться главным описанием текущего runtime-дизайна.

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
6. wrapper-level Telegram delivery retry/finalization through
   `tools/codex_schedule_delivery.py`, which invokes `tools/telegram_send.py`.

The generated digest lives at `digests/YYYY-MM-DD-daily-digest.md`.
Current-run manifests are required under `.state/runs/YYYY-MM-DD/`; a date-level
digest file alone is not enough to mark a scheduled run complete.

## Runbook Quick Links

| Need | Start here |
| --- | --- |
| New machine or new Cowork session | [`docs/cowork-onboarding.md`](./docs/cowork-onboarding.md) |
| Scheduled Codex runner | [`ops/codex-cli/README.md`](./ops/codex-cli/README.md) |
| Server/systemd/cron launch | [`docs/codex-cli-server-launch.md`](./docs/codex-cli-server-launch.md) |
| Tool contracts and local helper tests | [`tools/README.md`](./tools/README.md) |
| Production-like run reviews | [`docs/run-reviews/`](./docs/run-reviews/) |
| LLM benchmark suite | [`benchmark/README.md`](./benchmark/README.md) |

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
3. `build_daily_digest` produces the compact Russian `telegram_digest`
   markdown and `daily_brief` from compact artifacts only.
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
| [docs/cowork-onboarding.md](./docs/cowork-onboarding.md) | Онбординг: запуск в новой сессии и развёртывание на новой машине + готовый bootstrap prompt |
| [docs/runtime-architecture.md](./docs/runtime-architecture.md) | Canonical описание текущей runtime-архитектуры |
| [docs/mode-catalog.md](./docs/mode-catalog.md) | Canonical каталог режимов `Claude Cowork` |
| [docs/launch-rerun-dry-run.md](./docs/launch-rerun-dry-run.md) | Canonical reference по schedules, manual reruns и regression/parity dry-runs |
| [cowork/](./cowork) | Canonical runtime instructions: shared briefs, modes and adapters |
| [docs/agent-spec.md](./docs/agent-spec.md) | Legacy detailed spec; useful as reference, but not current canonical runtime layer |
| [docs/llm-jtbd-analysis.md](./docs/llm-jtbd-analysis.md) | Каталог LLM-задач (JTBD) |
| [docs/rss-api-audit.md](./docs/rss-api-audit.md) | Legacy source audit reference |
| [benchmark/README.md](benchmark/README.md) | LLM benchmark: метрики и инструкция |
| [prompts/](./prompts) | Legacy prompt layer kept for reference and migration history |
