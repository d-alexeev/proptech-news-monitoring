# Mode Prompt: scrape_and_enrich

Load shared context from:

- `cowork/shared/mission_brief.md`
- `cowork/shared/taxonomy_and_scoring.md`
- `cowork/shared/contracts.md`

Purpose:

- fetch and normalize article bodies only for shortlisted items;
- extract evidence, classify, score, and summarize;
- emit `enriched_item`, updated `story_brief`, and `run_manifest`.

Allowed inputs:

- shortlist shard
- source-specific adapters when provided
- shared briefs

Forbidden inputs:

- long-form human reference material
- evaluation datasets and goldens
- full raw source universe beyond shortlist
- digest archive
- stakeholder profiles

This is the only mode allowed to treat full article text as a primary working input.
Do not assemble daily, weekly, or stakeholder digests here.
