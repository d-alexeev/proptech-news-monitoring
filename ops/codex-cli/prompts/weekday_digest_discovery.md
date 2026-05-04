# Codex CLI Stage A: weekday_digest discovery

Run `monitor_sources only` for the `weekday_digest` schedule binding.

Use the Runner Source Discovery Prefetch preamble in the generated prompt as
canonical local source evidence. Do not repeat static RSS/HTTP fetches already
represented in the prefetch artifacts.

Allowed writes:

- `./.state/raw/{run_date}/`
- `./.state/shortlists/{run_date}/`
- `./.state/runs/{run_date}/`
- optional `./.state/change-requests/{request_date}/`

Do not run scrape_and_enrich, build_daily_digest, review_digest, Telegram
delivery, or article full-text fetching in this stage.

Final response must include:

- monitor_sources run id
- shortlist shard path
- raw shard path
- run manifest path
- source discovery status and source-level blockers
