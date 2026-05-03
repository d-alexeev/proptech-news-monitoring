<!-- Archived from PLANS.md by RT-M8 Plan Context Hygiene. Human review history only; not runtime context. -->

## Addendum: Codex CLI Server Launch Mode

### Summary

Этот addendum добавляет отдельный MVP launch mode для запуска агента через
`codex exec` на удалённом сервере. Он является orchestration wrapper поверх
существующих canonical schedules и runtime modes, а не новым source-facing
`Claude Cowork` mode.

Ключевой принцип: обычный запуск через `Claude Cowork` и canonical runtime layer
не меняются. Codex CLI mode живёт в отдельном `ops/` namespace, читает
`config/runtime/schedule_bindings.yaml` и mode prompts из `cowork/`, но не
становится частью `config/runtime/runtime_manifest.yaml`.

### Requirements

| ID | Requirement |
| --- | --- |
| CLI-R1 | Должен существовать отдельный launch mode для headless запуска через `codex exec` на сервере. |
| CLI-R2 | Launch mode не должен менять canonical schedules, mode contracts, source groups или `Claude Cowork` mode matrix. |
| CLI-R3 | Launch mode должен использовать существующие schedule bindings: `weekday_digest`, `weekly_digest`, optional `breaking_alert`. |
| CLI-R4 | Launch mode должен иметь prompt artifacts, пригодные для non-interactive Codex CLI запуска. |
| CLI-R5 | Launch mode должен иметь server wrapper с env loading, lock от параллельных запусков и run logging. |
| CLI-R6 | Prompt должен запрещать persistent edits в prompts/config/adapters/contracts во время scheduled run; persistent issues оформляются как `change_request`. |
| CLI-R7 | Должна быть документация по установке на сервере и systemd/cron запуску. |
| CLI-R8 | Должна быть проверка, что ordinary launch path не зависит от `ops/` artifacts. |

### Milestones

#### CLI-M1. Plan and Contract

- Goal: зафиксировать boundary Codex CLI mode до добавления runtime-adjacent
  артефактов.
- Scope: только `PLANS.md`.
- Likely files/artifacts to change: `PLANS.md`.
- Dependencies: существующие `schedule_bindings.yaml`, `docs/launch-rerun-dry-run.md`,
  `tools/README.md`.
- Risks: смешать external launch wrapper с canonical `Claude Cowork` modes.
- Acceptance criteria:
  - все исходные требования CLI-R1..CLI-R8 замаплены;
  - явно сказано, что runtime manifest не меняется;
  - explicit non-goals зафиксированы.
- Tests or verification steps:
  - manual review of this addendum.
- Explicit non-goals:
  - не добавлять новый source-processing mode;
  - не менять расписание;
  - не реализовывать production-grade deterministic runner.

#### CLI-M2. Isolated Codex CLI Artifacts

- Goal: добавить отдельный `ops/codex-cli/` launch pack для server-side
  `codex exec`.
- Scope: prompt artifacts, wrapper script, output/log directory conventions.
- Likely files/artifacts to change:
  - `ops/codex-cli/README.md`
  - `ops/codex-cli/prompts/weekday_digest.md`
  - `ops/codex-cli/prompts/weekly_digest.md`
  - `ops/codex-cli/prompts/breaking_alert.md`
  - `ops/codex-cli/run_schedule.sh`
- Dependencies: `codex exec`, Python venv, `.env`, Telegram helper scripts.
- Risks:
  - scheduled agent may edit source-of-truth files unless prompt boundaries are explicit;
  - concurrent runs may corrupt `.state/` if no lock is used.
- Acceptance criteria:
  - launch pack lives outside `cowork/` and `config/runtime/`;
  - wrapper accepts only known schedule IDs;
  - wrapper loads `.env`, activates `.venv` when present, creates `.state/codex-runs/`,
    and uses a lock directory;
  - prompts instruct Codex to follow canonical schedules without changing runtime source files.
- Tests or verification steps:
  - `bash -n ops/codex-cli/run_schedule.sh`;
  - static check that `runtime_manifest.yaml` does not reference `ops/codex-cli`;
  - prompt review for persistent edit guardrails.
- Explicit non-goals:
  - не запускать реальный network fetch или Telegram delivery during implementation;
  - не добавлять secrets или machine-local config;
  - не менять `tools/rss_fetch.py` or `tools/telegram_send.py`.

#### CLI-M3. Operator Documentation

- Goal: документировать server deployment MVP без изменения обычного запуска.
- Scope: server setup, auth, env, systemd/cron examples, operational notes.
- Likely files/artifacts to change:
  - `docs/codex-cli-server-launch.md`
  - optionally `docs/launch-rerun-dry-run.md`
- Dependencies: CLI-M2 artifacts.
- Risks: оператор может принять Codex CLI mode за canonical runtime source of truth.
- Acceptance criteria:
  - документация объясняет, где живёт mode и почему он isolated;
  - есть команды установки, smoke checks and scheduling examples;
  - явно указаны ограничения MVP и rollback/disable path.
- Tests or verification steps:
  - static link/path review;
  - shell snippet sanity review where applicable.
- Explicit non-goals:
  - не описывать full production orchestrator;
  - не менять onboarding для обычной Cowork-сессии как обязательный путь.

### Coverage Matrix

| Requirement | Covered by |
| --- | --- |
| CLI-R1 | CLI-M1, CLI-M2, CLI-M3 |
| CLI-R2 | CLI-M1, CLI-M2, CLI-M3 |
| CLI-R3 | CLI-M2, CLI-M3 |
| CLI-R4 | CLI-M2 |
| CLI-R5 | CLI-M2, CLI-M3 |
| CLI-R6 | CLI-M2 |
| CLI-R7 | CLI-M3 |
| CLI-R8 | CLI-M2, CLI-M3 |

### Current Implementation Status

| Milestone | Status |
| --- | --- |
| CLI-M1 | completed |
| CLI-M2 | completed |
| CLI-M3 | completed |
