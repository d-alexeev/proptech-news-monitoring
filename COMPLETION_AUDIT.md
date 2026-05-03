# COMPLETION_AUDIT.md

## Current Audit: RT-M6 Minimal Codex Runner Scraping Tooling

Audit date: 2026-05-04

Scope: RT-M2 through RT-M6 offline tooling and contracts for the reduced Codex
runner scraping tool set. This audit does not claim RT-M7 live scraping results
or future reachability of external sources.

### Summary

RT-M6 adds an offline runner integration map at
`config/runtime/mode-fixtures/runner_integration_map.yaml` and a validator check
for `--check runner-integration`. The map covers every configured source in
`daily_core` and `weekly_context`, assigns exactly one primary minimal tool path
per source, represents manual-only sources as no-fetch rows, and documents
source-level residual live-fetch risks.

RT-M7 remains pending. No live network fetch, Telegram delivery, CAPTCHA
automation, proxy handling, or permanent adapter fix was performed as part of
this audit.

### Requirement Audit

| Requirement | Implemented behavior | Status | Evidence |
| --- | --- | --- | --- |
| RT-R1 | RSS/Atom and static HTTP share the `tools/rss_fetch.py` JSON-in/JSON-out fetcher contract. | Implemented offline | `tools/README.md`; `tools/test_rss_fetch.py`; runner map rows for `rss` and `html_scrape`. |
| RT-R2 | iTunes lookup URLs use the same HTTP fetcher path via `kind=http`; no separate iTunes client was added. | Implemented offline | `tools/README.md`; runner map rows for `zillow_ios` and `rightmove_ios`; `tools/test_rss_fetch.py`. |
| RT-R3 | Static fetch results include HTTP metadata, final URL, soft-fail labels, and raw body/item data for adapter reasoning. | Implemented offline | `tools/rss_fetch.py`; `tools/README.md`; `tools/test_rss_fetch.py`. |
| RT-R4 | Browser automation is documented as a bounded fallback for configured `chrome_scrape` and explicit adapter fallback cases. | Implemented as contract | `tools/chrome_notes.md`; `config/runtime/mode-fixtures/runner_browser_fallback_similarweb.yaml`; runner map `chrome_scrape` rows. |
| RT-R5 | Browser fallback is not allowed for login, CAPTCHA, paywall bypass, proxy rotation, or manual-only sources. | Implemented as contract and validation | `tools/chrome_notes.md`; runner map blocked row; `--check runner-integration` rejects blocked fetch invocation. |
| RT-R6 | PDF extraction exists for enrichment-only Rightmove RNS PDF cases. | Implemented offline | `tools/pdf_extract.py`; `tools/test_pdf_extract.py`; `config/runtime/mode-fixtures/runner_pdf_extract_rightmove.yaml`; Rightmove optional fallback row. |
| RT-R7 | Source adapter resolution is validated against configured source groups and `cowork/adapters/source_map.md`. | Implemented offline | `tools/validate_runtime_artifacts.py --check adapters`; runner integration adapter checks. |
| RT-R8 | `monitor_sources` full-text boundaries are guarded by fixture validation. | Implemented offline | `tools/validate_runtime_artifacts.py --check full-text-boundary`; mode fixtures. |
| RT-R9 | `scrape_and_enrich` full-text handling is limited to shortlisted/enrichment contexts and body statuses remain `full`, `snippet_fallback`, or `paywall_stub`. | Implemented offline | `config/runtime/mode-fixtures/scrape_and_enrich_*`; `runner_pdf_extract_rightmove.yaml`; full-text boundary validator. |
| RT-R10 | Persistent source/tool failures are represented through change-request contracts rather than silent runtime workarounds. | Implemented offline | `config/runtime/change_request_schema.yaml`; change-request fixtures; validator fixture checks. |
| RT-R11 | Acceptance checks run offline without live source fetch, Telegram delivery, secrets, proxy services, or CAPTCHA solving. | Implemented | RT-M6 validation command set; runner integration map `validation_contract`. |
| RT-R12 | Inman remains a regular recurring source with explicit RSS/feed-based discovery coverage. | Implemented | `weekly_context` source row; `runner_fetcher_contract_inman.yaml`; runner map row with primary tool path `HTTP/RSS fetcher`. |

### Pending Or Out Of Scope

| Item | Status | Notes |
| --- | --- | --- |
| RT-R13 / RT-M7 live scraping pass | Pending | Requires bounded live test after offline RT-M6 gates pass. This audit makes no reachability claim for external sites. |
| Permanent adapter fixes | Out of scope for RT-M6 | Any persistent source issue discovered later should be handled by RT-M7 follow-up proposal or change-request artifacts. |
| Broad crawler behavior | Out of scope | The runner map preserves one configured source-to-tool path per source, not a generic crawler launch. |

### Residual Live-Fetch Risks

- External RSS, HTML, iTunes, Google Play, Similarweb, and publisher pages may
  change availability, markup, metadata shape, rate limits, or anti-bot behavior
  during RT-M7 or future scheduled runs.
- Offline fixture validation proves contract coverage, not live reachability or
  future stability of remote sources.
- Browser fallback remains a bounded public-page observation path. It must
  soft-fail on login, CAPTCHA, paywall, proxy, or manual-only conditions.
- REA Group Investor Centre remains `manual_only_permanent` and must not be
  fetched by the runner.
- Rightmove PDF extraction is enrichment-only for shortlisted public PDF links;
  it is not primary discovery and does not expand full text into
  `monitor_sources`.

### Verification Gates For RT-M6

Required gates:

- `PYTHONPYCACHEPREFIX=.pycache-local python3 -m py_compile tools/validate_runtime_artifacts.py tools/test_validate_runtime_artifacts.py`
- `python3 tools/test_validate_runtime_artifacts.py`
- `python3 tools/validate_runtime_artifacts.py --check adapters`
- `python3 tools/validate_runtime_artifacts.py --check fixtures`
- `python3 tools/validate_runtime_artifacts.py --check full-text-boundary`
- `python3 tools/validate_runtime_artifacts.py --check runner-integration`
- `python3 tools/validate_runtime_artifacts.py --check all`
- `git diff --check`

RT-M6 is complete only if those gates pass and `PLANS.md` marks RT-M6 complete
without marking RT-M7 complete.

## Historical Audit: Follow-Up Runtime Change-Request Layer

This historical section preserves an earlier completion audit for the follow-up
runtime change-request layer. It is not the current RT-M6 audit and its HEAD
and worktree notes refer to the older audit context.

### Scope

Этот аудит сравнивает текущую ветку с follow-up implementation plan из
[FOLLOW_UP_MINI_PLAN.md](./FOLLOW_UP_MINI_PLAN.md).

Базовый refactor-план из [PLANS.md](./PLANS.md) здесь не переаудируется подробно:
он уже был закрыт ранее. Этот документ оценивает именно follow-up слой:

- policy для внешнего раннера;
- `change_request` artifacts и intake workflow;
- canonical docs по runtime architecture, modes, launch/rerun flows;
- выравнивание legacy docs.

Аудит выполнен по состоянию на:

- `HEAD`: `d96ab22` (`Align legacy docs with canonical runtime layer`)
- рабочее дерево: чистое
- тип репозитория: prompt/config/contract-oriented, практически без исполняемого кода

### Audit Basis

Источники истины для аудита:

- [FOLLOW_UP_MINI_PLAN.md](./FOLLOW_UP_MINI_PLAN.md)
- [cowork/shared/change_request_policy.md](./cowork/shared/change_request_policy.md)
- [cowork/shared/contracts.md](./cowork/shared/contracts.md)
- [config/runtime/change_request_schema.yaml](./config/runtime/change_request_schema.yaml)
- [config/runtime/change_request_intake_workflow.md](./config/runtime/change_request_intake_workflow.md)
- [config/runtime/state_layout.yaml](./config/runtime/state_layout.yaml)
- source-facing mode contracts:
  - [config/runtime/mode-contracts/monitor_sources.yaml](./config/runtime/mode-contracts/monitor_sources.yaml)
  - [config/runtime/mode-contracts/scrape_and_enrich_gate.yaml](./config/runtime/mode-contracts/scrape_and_enrich_gate.yaml)
  - [config/runtime/mode-contracts/breaking_alert.yaml](./config/runtime/mode-contracts/breaking_alert.yaml)
- change-request fixtures:
  - [config/runtime/change-request-fixtures/sample_change_request.yaml](./config/runtime/change-request-fixtures/sample_change_request.yaml)
  - [config/runtime/change-request-fixtures/intake_dry_run.yaml](./config/runtime/change-request-fixtures/intake_dry_run.yaml)
  - [config/runtime/mode-fixtures/monitor_sources_blocked_manual_change_request.yaml](./config/runtime/mode-fixtures/monitor_sources_blocked_manual_change_request.yaml)
  - [config/runtime/mode-fixtures/scrape_and_enrich_scrape_failure_change_request.yaml](./config/runtime/mode-fixtures/scrape_and_enrich_scrape_failure_change_request.yaml)
  - [config/runtime/mode-fixtures/scrape_and_enrich_adapter_gap_change_request.yaml](./config/runtime/mode-fixtures/scrape_and_enrich_adapter_gap_change_request.yaml)
  - [config/runtime/mode-fixtures/breaking_alert_blocked_manual_change_request.yaml](./config/runtime/mode-fixtures/breaking_alert_blocked_manual_change_request.yaml)
- canonical docs:
  - [README.md](./README.md)
  - [docs/runtime-architecture.md](./docs/runtime-architecture.md)
  - [docs/mode-catalog.md](./docs/mode-catalog.md)
  - [docs/launch-rerun-dry-run.md](./docs/launch-rerun-dry-run.md)
- legacy-sensitive docs:
  - [docs/agent-spec.md](./docs/agent-spec.md)
  - [docs/rss-api-audit.md](./docs/rss-api-audit.md)
  - (docs/runbook.md removed in legacy cleanup)
- вторичный doc surface:
  - [docs/llm-jtbd-analysis.md](./docs/llm-jtbd-analysis.md)
  - [docs/daily-digest-mechanism-review.md](./docs/daily-digest-mechanism-review.md)
  - [docs/benchmark-design.md](./docs/benchmark-design.md)

### Status Model

В этом аудите статусы трактуются так:

- `Fully implemented`:
  требование закрыто на уровне source-of-truth artifacts этого репозитория и не
  требует дополнительной repo-side декомпозиции.
- `Partially implemented`:
  существенная artifact layer уже есть, но остаётся хотя бы один важный
  незакрытый хвост: либо operational adoption вне репозитория не подтверждена,
  либо в repo остаётся конфликтующий/невыравненный surface.
- `Not implemented`:
  нет достаточного repo-side слоя, чтобы считать требование закрытым.

Важно:

- этот аудит оценивает завершённость follow-up implementation plan в
  репозитории;
- он не утверждает, что внешний `Claude Cowork` runner уже реально переведён на
  новый contract surface и эмитит `change_request` в живом окружении;
- для этого потребовались бы внешние operational rehearsal artifacts, которых в
  репозитории сейчас нет.

### What Exists On This Branch

На ветке действительно присутствует follow-up source-of-truth layer:

- policy boundary для внешнего раннера в
  [cowork/shared/change_request_policy.md](./cowork/shared/change_request_policy.md)
- canonical `change_request` schema и lifecycle в
  [config/runtime/change_request_schema.yaml](./config/runtime/change_request_schema.yaml)
- canonical storage path в
  [config/runtime/state_layout.yaml](./config/runtime/state_layout.yaml)
- source-facing escalation contracts для:
  - `monitor_sources`
  - `scrape_and_enrich`
  - `breaking_alert`
- Codex-side intake workflow в
  [config/runtime/change_request_intake_workflow.md](./config/runtime/change_request_intake_workflow.md)
- canonical docs по architecture, modes и launch/rerun flows
- legacy markers в ключевых старых docs

При этом на ветке по-прежнему отсутствуют:

- repo-side исполняемый внешний runner;
- live artifact, реально выпущенный внешним runner'ом через
  `./.state/change-requests/...`;
- подтверждённый end-to-end rehearsal:
  external runner failure -> emitted `change_request` -> Codex intake -> plan ->
  implementation commit.

### Overall Verdict

- [FOLLOW_UP_MINI_PLAN.md](./FOLLOW_UP_MINI_PLAN.md) закрыт по milestone table:
  `TF1-TF8 = completed`
- `6 / 10` follow-up requirements are `Fully implemented`
- `4 / 10` requirements are `Partially implemented`
- `0 / 10` requirements are `Not implemented`

Ключевой вывод:

- follow-up plan закрыт качественно на уровне policy/config/contract/docs
  артефактов;
- но часть требований по смыслу относится к поведению внешнего раннера и к
  полному выравниванию всего doc surface, а это на текущей ветке ещё не
  подтверждено operational evidence;
- поэтому честный итог не “всё безоговорочно finished”, а “repo-side
  implementation done, operational adoption still pending”.

### Requirement-by-Requirement Audit

| Requirement | Status | Evidence | Notes |
| --- | --- | --- | --- |
| `F1` | Fully implemented | [cowork/shared/change_request_policy.md](./cowork/shared/change_request_policy.md), [README.md](./README.md), [docs/runtime-architecture.md](./docs/runtime-architecture.md) | Репозиторий явно объявлен master source of truth для runtime changes. |
| `F2` | Partially implemented | policy in [cowork/shared/change_request_policy.md](./cowork/shared/change_request_policy.md), guards in source-facing mode contracts and prompts | Repo-side запрет self-mutation зафиксирован, но нет operational proof, что внешний runner уже реально соблюдает его в другом окружении. |
| `F3` | Partially implemented | [config/runtime/change_request_schema.yaml](./config/runtime/change_request_schema.yaml), [config/runtime/state_layout.yaml](./config/runtime/state_layout.yaml), source-facing fixtures and contracts | Artifact shape и emission points описаны полностью, но live emitted `change_request` от внешнего runner'а на этой ветке отсутствует. |
| `F4` | Fully implemented | [config/runtime/change_request_intake_workflow.md](./config/runtime/change_request_intake_workflow.md), [config/runtime/change-request-fixtures/intake_dry_run.yaml](./config/runtime/change-request-fixtures/intake_dry_run.yaml) | Codex-side intake workflow описан и имеет dry-run walkthrough. |
| `F5` | Fully implemented | [docs/runtime-architecture.md](./docs/runtime-architecture.md), [README.md](./README.md) | Canonical architecture docs добавлены и связаны с runtime manifest. |
| `F6` | Fully implemented | [docs/mode-catalog.md](./docs/mode-catalog.md), [docs/launch-rerun-dry-run.md](./docs/launch-rerun-dry-run.md), [README.md](./README.md) | Есть актуальные docs по режимам и способам запуска/перезапуска. |
| `F7` | Partially implemented | legacy markers in [docs/agent-spec.md](./docs/agent-spec.md), [docs/rss-api-audit.md](./docs/rss-api-audit.md); `docs/runbook.md` removed in legacy cleanup | Основные legacy-sensitive docs выровнены, но вторичный doc surface всё ещё содержит старые `dedupe.json` / `delivery-log.json` narrative без legacy marker. |
| `F8` | Fully implemented | required fields in [config/runtime/change_request_schema.yaml](./config/runtime/change_request_schema.yaml), sample fixture, path lookup keys in [config/runtime/state_layout.yaml](./config/runtime/state_layout.yaml) | `run_id`, `mode`, `stage`, `url` и `evidence_refs` зафиксированы как обязательные поля. |
| `F9` | Fully implemented | lifecycle and transitions in [config/runtime/change_request_schema.yaml](./config/runtime/change_request_schema.yaml), workflow ownership in [config/runtime/change_request_intake_workflow.md](./config/runtime/change_request_intake_workflow.md) | Lifecycle/status model и ownership transitions заданы явно. |
| `F10` | Partially implemented | allowed vs forbidden workaround rules in [cowork/shared/change_request_policy.md](./cowork/shared/change_request_policy.md), escalation hooks in source-facing mode contracts | Правило оформлено в repo policy, но нет external-runner rehearsal, подтверждающего фактическое соблюдение этой границы. |

### Fully Implemented Requirements

- `F1`
- `F4`
- `F5`
- `F6`
- `F8`
- `F9`

### Partially Implemented Requirements

- `F2`
- `F3`
- `F7`
- `F10`

### Not Implemented Requirements

Отсутствуют.

### Misleading Documentation Or Status Claims

#### 1. `FOLLOW_UP_MINI_PLAN.md` всё ещё имеет top-level статус `proposed`

Проблема:

- в [FOLLOW_UP_MINI_PLAN.md](./FOLLOW_UP_MINI_PLAN.md) milestone table уже
  говорит `TF1-TF8 = completed`
- но в секции `## Status` по-прежнему стоит ``proposed``

Почему это вводит в заблуждение:

- документ одновременно выглядит и как неисполненный план, и как завершённый
  execution record
- это самый явный stale status claim на текущей ветке

#### 2. Часть вторичных docs всё ещё описывает старую `dedupe.json` /
`delivery-log.json` модель как активную

Проблема:

- [docs/llm-jtbd-analysis.md](./docs/llm-jtbd-analysis.md)
- [docs/daily-digest-mechanism-review.md](./docs/daily-digest-mechanism-review.md)
- [docs/benchmark-design.md](./docs/benchmark-design.md)

по-прежнему ссылаются на `dedupe.json`, `delivery-log.json` и старый narrative
как на текущую operational модель без явного legacy marker.

Почему это вводит в заблуждение:

- основные canonical docs уже переведены на `config/runtime/` + `cowork/`
- но вторичный аналитический/benchmark surface может спутать нового читателя

#### 3. В legacy-marked docs всё ещё живут процедурные примеры с
несуществующим `save_article.py`

Проблема:

- [docs/rss-api-audit.md](./docs/rss-api-audit.md) теперь честно помечен как
  legacy/reference (а `docs/runbook.md` удалён в legacy cleanup)
- но внутри всё ещё есть подробные шаги с `save_article.py`, которого в
  репозитории нет

Почему это всё ещё слегка вводит в заблуждение:

- если читать документ выборочно, можно решить, что script существует
- формально конфликт смягчён legacy banner'ом, но stale examples остаются

#### 4. Статус `TF4` можно неверно прочитать как “external runner уже реально
эмитит change_request”

Проблема:

- repo-side contracts и fixtures для `change_request` в source-facing modes
  действительно сделаны

Почему это может быть прочитано неверно:

- на этой ветке нет live operational proof artifact из внешнего runner
- завершённость milestone означает готовность source-of-truth слоя, а не
  подтверждённую runtime adoption во внешнем окружении

### Exact Next Tasks Needed For Full Completion

Ниже перечислены уже не follow-up milestones, а точные post-plan задачи, если
цель — довести систему до полного operational completion, а не только закрыть
repo-side contract/docs layer.

#### 1. Обновить top-level статус follow-up плана

Нужно:

- заменить `## Status` в [FOLLOW_UP_MINI_PLAN.md](./FOLLOW_UP_MINI_PLAN.md) с
  ``proposed`` на что-то вроде ``completed`` или `implemented_at_repo_layer`

Результат:

- исчезнет главный stale status claim на текущей ветке

#### 2. Провести первый живой rehearsal внешнего `change_request`

Нужно:

- в реальном внешнем `Claude Cowork` environment спровоцировать хотя бы один
  source-facing failure case:
  - blocked/manual source
  - или scrape failure / adapter gap
- убедиться, что runner:
  - не мутирует runtime files,
  - пишет `change_request` в ожидаемый path,
  - заполняет обязательные поля из schema

Результат:

- требования `F2`, `F3`, `F10` перейдут из contract-level readiness в
  operationally verified state

#### 3. Зафиксировать end-to-end intake rehearsal

Нужно:

- взять emitted `change_request`
- прогнать его через workflow из
  [config/runtime/change_request_intake_workflow.md](./config/runtime/change_request_intake_workflow.md)
- получить:
  - plan update
  - минимальный implementation diff
  - validation evidence
  - reviewable commit

Результат:

- появится не только dry-run fixture, но и реальный reference example процесса
  `change_request -> Codex intake -> commit`

#### 4. Доделать secondary docs alignment

Нужно:

- явно пометить как legacy/reference или архивировать:
  - [docs/llm-jtbd-analysis.md](./docs/llm-jtbd-analysis.md)
  - [docs/daily-digest-mechanism-review.md](./docs/daily-digest-mechanism-review.md)
  - [docs/benchmark-design.md](./docs/benchmark-design.md)
Результат:

- `F7` станет действительно закрытым для всего заметного doc surface, а не
  только для главных operator/reference docs

#### 5. Решить судьбу stale `save_article.py` примеров

Нужно:

- либо убрать procedural примеры с `save_article.py` из legacy docs,
- либо добавить сверхявную пометку `historical example; script absent from repo`,
- либо заменить ссылку на реально существующий replacement flow

Результат:

- legacy docs перестанут содержать полуоперационные примеры, которые невозможно
  буквально выполнить в текущем репозитории

### Final Assessment

Ветка выглядит сильно и последовательно:

- follow-up план реально реализован как repo-side source-of-truth layer;
- `change_request` policy, schema, storage path, source-facing guards, intake
  workflow и canonical docs присутствуют и связаны между собой;
- ключевой remaining gap теперь не в проектировании, а в operational adoption и
  в дочистке вторичного doc surface.

Итоговая формулировка:

- follow-up plan **завершён по артефактам репозитория**;
- full operational completion **ещё требует живого external-runner rehearsal и
  финального doc cleanup вокруг secondary legacy materials**.
