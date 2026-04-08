# Mode Prompt: build_weekly_digest

Load shared context from:

- `cowork/shared/mission_brief.md`
- `cowork/shared/taxonomy_and_scoring.md`
- `cowork/shared/contracts.md`

Purpose:

- aggregate the current week from compact daily artifacts;
- load only limited prior weekly memory for continuity;
- prepare the weekly aggregation package before trend synthesis and final weekly rendering.

Allowed inputs:

- current-week `daily_brief`
- limited prior `weekly_brief`
- weekly and weekday schedule bindings

Forbidden inputs:

- raw candidates
- `./.state/raw/`
- `./.state/enriched/`
- full article bodies
- `./.state/articles/`
- full digest archive
- long-form human reference material
- evaluation datasets and goldens
- stakeholder profiles

This mode should not depend on the full historical digest corpus.
Use compact weekly memory, not raw archives.
Include only daily briefs from the target ISO week and matching weekday delivery profile.
