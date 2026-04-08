# Mode Catalog

Этот документ — canonical краткий каталог текущих runtime modes для
`Claude Cowork`-дизайна.

Source-of-truth для mode details:

- [`config/runtime/runtime_manifest.yaml`](../config/runtime/runtime_manifest.yaml)
- [`config/runtime/mode-contracts/`](../config/runtime/mode-contracts)
- [`cowork/modes/`](../cowork/modes)

## `monitor_sources`

- Purpose: discovery, primary triage, shortlist emission.
- Primary inputs: source-group config, thresholds, checkpoint, recent story
  index, resolved adapters only when needed.
- Main outputs: `raw_candidate[]`, `shortlisted_item[]`, `run_manifest`,
  optional `change_request`.
- Hard guard: не читает full article text и не должен менять prompts/config/adapters.

## `scrape_and_enrich`

- Purpose: full-text fetch only for shortlist, normalization, extraction,
  scoring, summarization.
- Primary inputs: shortlist shard, resolved adapters, shared briefs.
- Main outputs: `enriched_item[]`, updated `story_brief`, `run_manifest`,
  optional `change_request`.
- Hard guard: это единственный mode, где full article text допустим как primary
  working input.

## `build_daily_digest`

- Purpose: daily selection, anti-repeat, contextual continuation, markdown
  rendering, `daily_brief` emission.
- Primary inputs: daily-window enriched items, recent `story_brief`,
  recent `daily_brief`, delivery metadata.
- Main outputs: daily digest markdown, `daily_brief`, `run_manifest`.
- Hard guard: не читает raw shards, article bodies или past markdown archive.

## `review_digest`

- Purpose: QA review готового digest без его переписывания.
- Primary inputs: digest markdown, kept/dropped compact artifacts,
  `daily_brief` or `weekly_brief`, `run_manifest`.
- Main outputs: grouped QA review report.
- Hard guard: не делает delivery и не превращается в альтернативный digest.

## `build_weekly_digest`

- Purpose: weekly aggregation по текущей неделе, bounded weekly memory,
  trend synthesis, `weekly_brief` emission.
- Primary inputs: current-week `daily_brief`, limited prior `weekly_brief`,
  weekly aggregation outputs.
- Main outputs: weekly digest markdown, `weekly_brief`, `run_manifest`.
- Hard guard: не читает raw shards, full article bodies или весь digest archive.

## `breaking_alert`

- Purpose: alert-only path для immediate high-priority items.
- Primary inputs: recent enriched items, recent `story_brief`, alert thresholds,
  `breaking_alert` schedule bindings.
- Main outputs: alert payload, `run_manifest`, optional `change_request`.
- Hard guard: не зависит от daily/weekly digest generation.

## `stakeholder_fanout`

- Purpose: downstream personalization одного `daily_brief` или `weekly_brief`
  под один stakeholder profile.
- Primary inputs: one brief, one stakeholder profile.
- Main outputs: one profile-specific digest, `run_manifest`.
- Hard guard: не входит в base daily/weekly critical path и не тянет raw/full-text.
