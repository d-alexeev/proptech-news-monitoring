# Codex CLI Server Launch MVP

## Purpose

This document describes the MVP path for running PropTech News Monitoring on a
remote server through `codex exec`.

This is an optional launch mode. It does not replace the canonical `Claude
Cowork` runtime design and does not change the schedule bindings, mode
contracts, source groups, or prompt source of truth.

Canonical runtime remains:

- `config/runtime/runtime_manifest.yaml`
- `config/runtime/schedule_bindings.yaml`
- `cowork/shared/`
- `cowork/modes/`
- `cowork/adapters/`

Codex CLI server artifacts live under `ops/codex-cli/` and are intentionally not
referenced by `config/runtime/runtime_manifest.yaml`.

## Architecture

```text
systemd timer or cron
  -> ops/codex-cli/run_schedule.sh <schedule_id>
      -> codex exec
          -> reads canonical runtime files
          -> performs the requested schedule path
          -> writes .state/ and digests/ artifacts
          -> sends Telegram delivery when configured
```

Supported schedule IDs:

- `weekday_digest`
- `weekly_digest`
- `breaking_alert`

## Server Setup

Install the repository and Python helper dependencies:

```bash
git clone <repo-url> /opt/proptech-news-monitoring
cd /opt/proptech-news-monitoring
python3 -m venv .venv
. .venv/bin/activate
pip install -r tools/requirements.txt
```

Install and authenticate Codex CLI on the server:

```bash
codex login
codex --version
```

Create `.env` in the repository root. Do not commit it.

```bash
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
TELEGRAM_MESSAGE_THREAD_ID=
HTTP_USER_AGENT="PropTechMonitor/1.0 (+you@example.com)"
```

If `codex` is not on the service user's `PATH`, set `CODEX_BIN` when invoking
the wrapper.

## Manual Smoke Runs

Run from the repository root:

```bash
ops/codex-cli/run_schedule.sh weekday_digest
ops/codex-cli/run_schedule.sh weekly_digest
ops/codex-cli/run_schedule.sh breaking_alert
```

The wrapper writes:

- JSONL Codex events to `.state/codex-runs/*-events.jsonl`
- the final Codex response to `.state/codex-runs/*-last-message.txt`

The wrapper uses a lock directory per schedule under `.state/codex-runs/` to
avoid overlapping runs.

## systemd Example

Example service template, saved as `proptech-codex@.service`:

```ini
[Unit]
Description=PropTech monitor Codex schedule %i

[Service]
Type=oneshot
WorkingDirectory=/opt/proptech-news-monitoring
Environment=CODEX_BIN=/usr/local/bin/codex
ExecStart=/opt/proptech-news-monitoring/ops/codex-cli/run_schedule.sh %i
```

Example weekday timer, saved as `proptech-codex-weekday.timer`:

```ini
[Unit]
Description=PropTech weekday digest timer

[Timer]
OnCalendar=Mon..Fri 09:00
Persistent=true
Unit=proptech-codex@weekday_digest.service

[Install]
WantedBy=timers.target
```

Example weekly timer, saved as `proptech-codex-weekly.timer`:

```ini
[Unit]
Description=PropTech weekly digest timer

[Timer]
OnCalendar=Fri 17:00
Persistent=true
Unit=proptech-codex@weekly_digest.service

[Install]
WantedBy=timers.target
```

Example alert timer, saved as `proptech-codex-alert.timer`:

```ini
[Unit]
Description=PropTech breaking alert timer

[Timer]
OnCalendar=hourly
Persistent=true
Unit=proptech-codex@breaking_alert.service

[Install]
WantedBy=timers.target
```

For MVP rollout, enable `weekday_digest` and `weekly_digest` first. Add
`breaking_alert` after scheduled digest runs are stable.

## cron Example

```cron
0 9 * * 1-5 cd /opt/proptech-news-monitoring && ops/codex-cli/run_schedule.sh weekday_digest
0 17 * * 5 cd /opt/proptech-news-monitoring && ops/codex-cli/run_schedule.sh weekly_digest
```

Hourly alert check:

```cron
0 * * * * cd /opt/proptech-news-monitoring && ops/codex-cli/run_schedule.sh breaking_alert
```

## Safety Rules

Scheduled Codex runs may write only operational artifacts:

- `.state/`
- `digests/`

Scheduled runs must not edit source-of-truth files:

- `cowork/`
- `config/runtime/`
- `docs/`
- `tools/`
- `prompts/`
- `benchmark/`
- `README.md`
- `AGENTS.md`
- `PLANS.md`

If Codex discovers that a persistent fix is required, it should emit a
`change_request` according to `cowork/shared/change_request_policy.md`.

## Disable and Rollback

To disable server launch without touching the runtime layer:

```bash
systemctl --user disable --now proptech-codex-weekday.timer
systemctl --user disable --now proptech-codex-weekly.timer
systemctl --user disable --now proptech-codex-alert.timer
```

Or remove/comment the matching cron lines.

Because `ops/codex-cli/` is isolated, disabling timers or cron entries returns
the project to the ordinary Cowork/manual launch posture without changing
canonical runtime files.

## MVP Limitations

- Codex CLI launch is agentic orchestration, not a deterministic production
  runner.
- The server must have network access and valid Codex authentication.
- Full article text remains restricted to `scrape_and_enrich`.
- Delivery depends on Telegram environment variables.
- Persistent runtime changes still go through repository change requests and
  review, not scheduled runs.
