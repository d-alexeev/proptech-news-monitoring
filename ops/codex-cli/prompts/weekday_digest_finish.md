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

Use the generated prompt's schedule run id timestamp for current-run finish artifacts.
For example, if the schedule run id starts with `<run timestamp>`, Stage C must
prepare current-run finish artifacts including
`scrape_and_enrich__<run timestamp>__daily_core` and
`build_daily_digest__<run timestamp>__telegram_digest` manifests through the
finish draft contract below. Do not reuse prior `.state/enriched/`,
`.state/runs/`, `.state/briefs/`, or digest artifacts as evidence that this
stage completed.

## Language Requirement

For `delivery_profile = telegram_digest`, all final human-facing digest prose
must be in Russian.

Translate or summarize English source material into Russian before writing:

- `enriched_items[].analyst_summary`
- `enriched_items[].why_it_matters`
- `enriched_items[].avito_implication`
- `enriched_items[].evidence_points`
- `daily_brief.selection_notes`
- `daily_brief.story_cards[].analyst_summary`
- `daily_brief.story_cards[].why_it_matters`
- `daily_brief.story_cards[].avito_implication`
- `daily_brief.story_cards[].evidence_notes`
- `digest_markdown`

Do not emit an English-only `telegram_digest`. Source titles, company names,
product names, URLs, and short source names may remain in their original
language, but headings, labels, summaries, implications, and evidence notes must
be Russian.

Do not use English business jargon in Russian editorial prose when a Russian
equivalent exists. Translate terms such as `agent tooling`, `lead quality`,
`profit pools`, `pre-market`, `source discovery`, `snippet fallback`,
`paywall stubs`, `unit economics`, `tech stack`, and `traffic monetization`.

## Template, Length, and Preview Requirement

For `delivery_profile = telegram_digest`, `digest_markdown` must follow the compact
daily template:

- title line: `# PropTech Monitor Daily | D month YYYY` with a Russian month name;
- main section: `## ТОП СИГНАЛЫ`;
- at most 3 story cards;
- each card includes `### <emoji> <title>`, `Score: XX | <topic/category> | <short regions> | [Источник](url)`, `**Что это значит:**`, and `**Для Avito:**`;
- final line starts with `Статус запуска:`;
- no nested story bullets;
- raw markdown target <= 3000 characters; hard maximum <= 3400 characters.

Each enriched item and story card must include `lead_image`. Use
`lead_image.status = available` only when article prefetch found image metadata
for that same URL. Add `telegram_preview` to the finish draft:

```json
{
  "status": "available",
  "preview_url": "https://article-url.example",
  "source_story_id": "story_id",
  "lead_image_url": "https://image-url.example",
  "reason": "first_top_signal_has_lead_image"
}
```

If no selected top signal has image metadata, use:

```json
{
  "status": "unavailable",
  "preview_url": null,
  "source_story_id": null,
  "lead_image_url": null,
  "reason": "no_selected_top_signal_with_lead_image"
}
```

## Required Finish Draft

Write exactly one compact JSON draft to the generated prompt's `Finish draft path`.
Do not write final .state/enriched, `.state/runs`, `.state/briefs`, or
`digests/*.md` artifacts directly. The wrapper will validate and materialize
those files through `tools/stage_c_finish.py`.

The draft JSON must contain:

- `schema_version: 1`
- `run_id`
- `run_date`
- `source_group`
- `delivery_profile`
- `enriched_items`
- `daily_brief`
- `digest_markdown`
- `qa_review`
- `telegram_preview`
- `telegram_delivery`

Each `enriched_items[]` entry must match a current-run shortlisted URL and a
current-run article prefetch result entry by `url` or `canonical_url`.

For `body_status = full`, include the matched `article_file` path from the
article prefetch result. For `snippet_fallback` or `paywall_stub`, keep
`article_file` null unless the prefetch result explicitly provides a safe file.

`digest_markdown` must be final human-readable digest markdown. It must not
contain `.state/`, `.state/articles/`, `article_file`, timestamped run ids,
operator notes, or full article bodies.

`qa_review.status` must be `validated` or `warnings`; `skipped` is not
acceptable for a 95% production-ready test-run. `critical_findings_count` must
be `0`.

Do not read .state/articles/ from digest or review modes. Do not pass article
body text into digest markdown, review markdown, final response, or run-review
docs.

Final response must report source discovery, article prefetch, enrichment,
digest generation, QA/review, Telegram delivery, incomplete items, and change
requests as separate stage statuses.
