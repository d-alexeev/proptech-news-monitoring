# Codex CLI Stage C: weekday_digest finish

Run the remaining `weekday_digest` modes after discovery and article prefetch:

1. `scrape_and_enrich`
2. `build_daily_digest`
3. optional `review_digest`
4. Telegram delivery when configured

Use the generated prompt's source prefetch artifacts and Stage B article prefetch manifest
as local evidence. `scrape_and_enrich` may read article files
only when the article prefetch manifest entry matches a current-run shortlisted
URL.

Do not read .state/articles/ from digest or review modes. Do not pass article
body text into digest markdown, review markdown, final response, or run-review
docs.

Final response must report source discovery, article prefetch, enrichment,
digest generation, QA/review, Telegram delivery, incomplete items, and change
requests as separate stage statuses.
