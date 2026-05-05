# Mode Prompt: build_daily_digest

Load shared context from:

- `cowork/shared/mission_brief.md`
- `cowork/shared/taxonomy_and_scoring.md`
- `cowork/shared/contracts.md`

Purpose:

- select daily top items and weak signals from compact artifacts;
- suppress redundant repeats using recent compact digest memory;
- add contextual continuation where justified from `story_brief`, not from article bodies;
- render the human-readable daily digest;
- emit a structured `daily_brief` for weekly synthesis and stakeholder fanout.

Allowed inputs:

- enriched items for the daily window
- recent `story_brief`
- recent `daily_brief`
- current-run selection outputs
- delivery profile metadata from schedule bindings

Forbidden inputs:

- raw candidates
- shortlist shards
- full article bodies
- `./.state/articles/`
- digest markdown archive
- long-form human reference material
- evaluation datasets and goldens
- stakeholder profiles

This mode should work from compact artifacts only.
Use `recent daily_brief` for anti-repeat decisions and `story_brief.last_digest_refs` plus `story_brief.summary_line` for context.
Render markdown and `daily_brief` from selected compact records only.
Do not read past markdown digests or `./.state/articles/` in this mode.
Do not perform downstream personalization here.
If all current-window enriched records available to selection have `body_status = snippet_fallback`, the run may still render, but it must be labeled `partial_digest` in `daily_brief.render_metadata.digest_status` and in selection notes.
Such a digest must not look production-clean: include compact evidence limitation notes and keep durable `url` and `canonical_url` values on each selected story card.
Do not read full article bodies, `article_file`, or `./.state/articles/` to resolve an all-snippet condition.

When emitting the build run manifest, keep `run_manifest.status = completed`
only to mean the digest artifact was generated. Set
`run_manifest.operator_report.digest_generation` from evidence available to this
mode, such as all-snippet enrichment records or explicit selection evidence
limits. Use `status: generated`, `digest_status: partial_digest` or
`non_canonical_digest`, and `canonical: false` when those local inputs make the
digest non-canonical. Do not infer source discovery completeness from this mode;
the weekday wrapper/final operator report synthesizes cross-stage source
discovery, enrichment, review, and delivery readiness from compact stage
manifests and operator reports.

## Delivery constraints

These rules apply to the digest body that is written to the canonical weekday digest
markdown path `./digests/{digest_date}-daily-digest.md` and subsequently sent to
Telegram via `tools/telegram_send.py`.

**Language:**
For `telegram_digest`, the digest body must be Russian-only editorial prose.
Translate or summarize English source evidence into Russian. Keep source names,
company names, product names, article titles in links, and URLs in their
original language when needed, but do not render English section headings,
labels, summaries, or Avito implications.
Do not leave English business jargon in the visible prose when a Russian
equivalent exists. Translate terms such as `agent tooling`, `lead quality`,
`profit pools`, `pre-market`, `source discovery`, `snippet fallback`,
`paywall stubs`, `unit economics`, `tech stack`, and `traffic monetization`.

**Template for `telegram_digest`:**
Use this exact visible structure so daily runs are stable:

```md
# PropTech Monitor Daily | D month YYYY

## ТОП СИГНАЛЫ

### <emoji> <title>
Score: XX | <topic/category> | <short regions> | [Источник](url)

<analyst_summary>

**Что это значит:** <why_it_matters>

**Для Avito:** <avito_implication>

Статус запуска: источники X/Y | статьи A/B | качество: <validated/warnings>; <short scrape-quality note>
```

Rules:
- Use a Russian month name in the title, for example `4 мая 2026`.
- Render up to 5 signal cards.
- Pick one relevant emoji per card; do not use emoji elsewhere.
- `Score:` is the only allowed English fixed label in the visible digest.
- Use compact Russian topic/category labels and short region labels such as
  `US`, `UK`, `AU`, `EU`, `GCC`, `Global`.
- The `Источник` link points to the article/source URL for that card.
- End with exactly one `Статус запуска:` line.
- Do not add separate `Стоит отслеживать`, `Слабые сигналы`,
  `Вывод для Авито`, or `Качество доказательств` sections in the compact
  Telegram daily template.

**Length budget for `telegram_digest`:**
- Target raw markdown length: <= 3000 characters before Telegram HTML conversion.
- Hard maximum raw markdown length: <= 3400 characters.
- `## ТОП СИГНАЛЫ`: up to 5 story cards.
- Each story field must be one short paragraph, with no nested story bullets.

If evidence is mixed or partial, keep the evidence-quality disclosure but compress it
into the final `Статус запуска:` line. Do not include source counts in multiple sections.

**Preview policy for `telegram_digest`:**
Prefer ordering the first rendered top signal so it has `lead_image.status = available`.
The first story source URL is used as the Telegram large link preview URL.
If no top signal has usable image metadata, render and deliver the digest without preview.

**File write rule:**
Always write the digest file using a full overwrite (`Write`), never a partial edit (`Edit`).
Reason: `Edit` leaves content from prior runs in the file tail, causing mixed-run output.
If a digest file for the current date already exists, it must be replaced entirely.

**Path contract:**
For new weekday digest runs, `daily_brief.markdown_path` must equal the canonical
markdown path `./digests/{digest_date}-daily-digest.md`. Older `*-daily.md` archive
paths are legacy compatibility references only and must not be used as the current
output path for new runs.

**Operator metadata:**
`.state/` path references and full `run_id` strings (e.g. `build_daily_digest__20260422T230500Z__daily_core`)
belong in `run_manifest` only. Do not include them in the digest body.
- Keep stage readiness metadata in `run_manifest.operator_report`, not in the digest body.
- Operator notes (blockquotes referencing previous runs, internal paths) must not appear in the body.
- The footer line may include the mode name and date but must not include the full timestamped run_id.
  Use the form: `mode: build_daily_digest | 22.04.2026` — not the full `run_id`.

**Body formatting:**
The `telegram_send` adapter (HTML parse_mode) converts standard GFM to Telegram-compatible HTML
automatically. You may use standard GFM in the `.md` file:
- `## Heading` → rendered as bold in Telegram
- `**bold**` → rendered as bold in Telegram
- `---` → removed by adapter (use blank lines for visual separation in the .md file)
- `[text](url)` and `` `code` `` → rendered correctly in Telegram

No dual syntax or manual Telegram escaping is required in the body.
