# Mode Prompt: scrape_and_enrich

Load shared context from:

- `cowork/shared/mission_brief.md`
- `cowork/shared/taxonomy_and_scoring.md`
- `cowork/shared/contracts.md`
- `cowork/adapters/source_map.md` when shortlisted `source_id` values resolve to adapters

Purpose:

- fetch and normalize article bodies only for shortlisted items;
- extract evidence, classify, score, and summarize;
- emit `enriched_item`, updated `story_brief`, and `run_manifest`.

Allowed inputs:

- shortlist shard
- only the source-specific adapters resolved for shortlisted items
- shared briefs

Outputs:

- `./.state/enriched/{run_date}/{run_id}.json`
- updated `./.state/stories/{first_seen_month}/{story_id}.json`
- `./.state/runs/{run_date}/{run_id}.json`

Forbidden inputs:

- long-form human reference material
- evaluation datasets and goldens
- full raw source universe beyond shortlist
- `./.state/raw/`
- digest archive
- stakeholder profiles

This is the only mode allowed to treat full article text as a primary working input.
Begin the fetch queue only from `shortlisted_item` entries with `triage_decision = shortlist`.
Candidates dropped or never emitted into the shortlist shard must never trigger body fetch.
Normalize every fetch outcome into `body_status = full | snippet_fallback | paywall_stub`.
Capture 2-4 `evidence_points` for `full`, 1-2 for `snippet_fallback`, and none for `paywall_stub`.
Emit downstream-ready `analyst_summary`, `why_it_matters`, `avito_implication`, `story_id`, and `source_quality`.
Do not preload the whole adapter directory; resolve `source_id -> adapter` first.
Do not assemble daily, weekly, or stakeholder digests here.
